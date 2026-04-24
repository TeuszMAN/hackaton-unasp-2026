"""
Router — Necessidades de Crise.

Endpoints para registrar e consultar demandas emergenciais. O registro
recebe descrição em linguagem natural e dispara extração de habilidades
requeridas + inferência de nível de urgência via watsonx.ai (Granite).
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


router = APIRouter(prefix="/api/v1/necessidades", tags=["Necessidades"])


async def _enriquecer_necessidade(necessidade_id: uuid.UUID) -> None:
    db: Session = SessionLocal()
    try:
        n = db.get(models.Necessidade, necessidade_id)
        if n is None:
            return

        ia = get_ia_service()
        extracao = await ia.extrair_requisitos_necessidade(n.descricao_crise)
        n.habilidades_requeridas = extracao.habilidades_requeridas
        # Só sobrescreve a urgência se o usuário não forneceu explicitamente
        if n.nivel_urgencia is None:  # defensivo
            n.nivel_urgencia = extracao.nivel_urgencia

        if (
            n.latitude is None
            and n.longitude is None
            and n.endereco_texto
        ):
            coords = await geocodificar(n.endereco_texto)
            if coords:
                n.latitude, n.longitude = coords

        db.commit()
    finally:
        db.close()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.TaskAceita,
    summary="Registrar necessidade emergencial (assíncrono)",
    description=(
        "Recebe uma descrição em linguagem natural de uma situação de crise. "
        "Dispara, em background, a extração das habilidades requeridas e a "
        "inferência do nível de urgência via watsonx.ai, além da geocodificação "
        "do endereço. Retorna 202 imediatamente com os IDs de acompanhamento."
    ),
)
def registrar_necessidade(
    payload: schemas.NecessidadeCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    n = models.Necessidade(
        instituicao_id=payload.instituicao_id,
        descricao_crise=payload.descricao_crise,
        habilidades_requeridas=[],
        endereco_texto=payload.endereco,
        latitude=payload.latitude,
        longitude=payload.longitude,
        nivel_urgencia=payload.nivel_urgencia or models.NivelUrgencia.alto,
    )
    db.add(n)
    db.commit()
    db.refresh(n)

    background_tasks.add_task(_enriquecer_necessidade, n.id)

    return schemas.TaskAceita(
        task_id=uuid.uuid4(),
        resource_id=n.id,
        mensagem="Necessidade registrada — extração em andamento.",
    )


@router.get(
    "",
    response_model=list[schemas.NecessidadeOut],
    summary="Listar necessidades",
)
def listar_necessidades(
    status_filter: models.StatusNecessidade | None = Query(None, alias="status"),
    urgencia: models.NivelUrgencia | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.Necessidade)
    if status_filter is not None:
        stmt = stmt.where(models.Necessidade.status == status_filter)
    if urgencia is not None:
        stmt = stmt.where(models.Necessidade.nivel_urgencia == urgencia)
    stmt = stmt.order_by(models.Necessidade.criado_em.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get(
    "/{necessidade_id}",
    response_model=schemas.NecessidadeOut,
    summary="Consultar necessidade",
)
def obter_necessidade(necessidade_id: uuid.UUID, db: Session = Depends(get_db)):
    n = db.get(models.Necessidade, necessidade_id)
    if n is None:
        raise HTTPException(status_code=404, detail="Necessidade não encontrada.")
    return n
