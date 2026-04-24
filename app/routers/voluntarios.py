"""
Router — Voluntários.

Endpoints para cadastro, consulta e atualização de voluntários. O
cadastro recebe relato em linguagem natural e delega ao serviço de IA
(watsonx.ai via interface `IAExtracaoService`) a extração das habilidades
normalizadas contra a taxonomia controlada.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal, get_db
from app.services.ai import get_ia_service
from app.services.geocoding import geocodificar


router = APIRouter(prefix="/api/v1/voluntarios", tags=["Voluntários"])


# ---------------------------------------------------------------------------
# Background: enriquecimento via IA + geocoding
# ---------------------------------------------------------------------------
async def _enriquecer_voluntario(voluntario_id: uuid.UUID) -> None:
    """Chama o serviço de IA e o geocoder, atualiza o voluntário no banco."""
    db: Session = SessionLocal()
    try:
        voluntario = db.get(models.Voluntario, voluntario_id)
        if voluntario is None:
            return

        ia = get_ia_service()
        if voluntario.relato_original:
            extracao = await ia.extrair_habilidades_voluntario(voluntario.relato_original)
            voluntario.habilidades = extracao.habilidades

        if (
            voluntario.latitude is None
            and voluntario.longitude is None
            and voluntario.endereco_texto
        ):
            coords = await geocodificar(voluntario.endereco_texto)
            if coords:
                voluntario.latitude, voluntario.longitude = coords

        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /api/v1/voluntarios
# ---------------------------------------------------------------------------
@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.TaskAceita,
    summary="Cadastrar voluntário (assíncrono)",
    description=(
        "Recebe um relato livre do voluntário e dispara, em background, a "
        "extração de habilidades via watsonx.ai (Granite) e a geocodificação "
        "do endereço. Retorna imediatamente 202 com o `task_id` e o `resource_id` "
        "(id do voluntário) — consulte `GET /api/v1/voluntarios/{id}` para "
        "acompanhar o enriquecimento."
    ),
)
def cadastrar_voluntario(
    payload: schemas.VoluntarioCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not payload.consentimento_lgpd:
        raise HTTPException(
            status_code=400,
            detail="Consentimento LGPD explícito é obrigatório para cadastro.",
        )

    voluntario = models.Voluntario(
        nome=payload.nome,
        telefone=payload.telefone,
        email=payload.email,
        relato_original=payload.relato,
        habilidades=[],
        endereco_texto=payload.endereco,
        latitude=payload.latitude,
        longitude=payload.longitude,
        consentimento_lgpd=payload.consentimento_lgpd,
    )
    db.add(voluntario)
    db.commit()
    db.refresh(voluntario)

    background_tasks.add_task(_enriquecer_voluntario, voluntario.id)

    return schemas.TaskAceita(
        task_id=uuid.uuid4(),
        resource_id=voluntario.id,
        mensagem="Cadastro recebido — enriquecimento em andamento.",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/voluntarios
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=list[schemas.VoluntarioOut],
    summary="Listar voluntários",
    description="Lista voluntários cadastrados com filtros opcionais.",
)
def listar_voluntarios(
    disponibilidade: models.StatusVoluntario | None = Query(None),
    habilidade: str | None = Query(
        None,
        description="Filtra voluntários que possuam ao menos a habilidade informada (código da taxonomia).",
    ),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.Voluntario)
    if disponibilidade is not None:
        stmt = stmt.where(models.Voluntario.disponibilidade == disponibilidade)
    if habilidade:
        stmt = stmt.where(models.Voluntario.habilidades.any(habilidade))
    stmt = stmt.limit(limit).order_by(models.Voluntario.criado_em.desc())
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# GET /api/v1/voluntarios/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{voluntario_id}",
    response_model=schemas.VoluntarioOut,
    summary="Consultar voluntário",
)
def obter_voluntario(voluntario_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Voluntario, voluntario_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Voluntário não encontrado.")
    return v


# ---------------------------------------------------------------------------
# PATCH /api/v1/voluntarios/{id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{voluntario_id}",
    response_model=schemas.VoluntarioOut,
    summary="Atualizar perfil do voluntário",
)
def atualizar_voluntario(
    voluntario_id: uuid.UUID,
    payload: schemas.VoluntarioUpdate,
    db: Session = Depends(get_db),
):
    v = db.get(models.Voluntario, voluntario_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Voluntário não encontrado.")

    data = payload.model_dump(exclude_unset=True)
    for campo, valor in data.items():
        setattr(v, campo, valor)
    db.commit()
    db.refresh(v)
    return v
