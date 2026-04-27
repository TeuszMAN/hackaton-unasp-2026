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
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal, get_db
from app.services import auth as auth_svc
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
    response_model=schemas.VoluntarioCadastroAceito,
    responses={
        409: {
            "description": "Voluntário já cadastrado com o mesmo telefone ou e-mail.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Voluntário já cadastrado com este telefone. "
                            "Não é permitido cadastrar o mesmo voluntário duas vezes. "
                            "Utilize o ID existente: <uuid>"
                        )
                    }
                }
            },
        }
    },
    summary="Cadastrar voluntário (assíncrono)",
    description=(
        "Recebe um relato livre do voluntário e dispara, em background, a "
        "extração de habilidades via watsonx.ai (Granite) e a geocodificação "
        "do endereço. Retorna imediatamente 202 com o `task_id` e o `resource_id` "
        "(id do voluntário) — consulte `GET /api/v1/voluntarios/{id}` para "
        "acompanhar o enriquecimento. "
        "Retorna 409 se já existe um voluntário com o mesmo telefone ou e-mail."
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

    filtros = [models.Voluntario.telefone == payload.telefone]
    if payload.email:
        filtros.append(models.Voluntario.email == payload.email)

    duplicado = db.execute(
        select(models.Voluntario).where(or_(*filtros)).limit(1)
    ).scalar_one_or_none()

    if duplicado is not None:
        campo = "e-mail" if payload.email and duplicado.email == payload.email else "telefone"
        raise HTTPException(
            status_code=409,
            detail=(
                f"Voluntário já cadastrado com este {campo}. "
                "Não é permitido cadastrar o mesmo voluntário duas vezes. "
                f"Utilize o ID existente: {duplicado.id}"
            ),
        )

    if payload.instituicao_id is not None:
        instituicao = db.get(models.Instituicao, payload.instituicao_id)
        if instituicao is None:
            raise HTTPException(
                status_code=404,
                detail=f"Instituição {payload.instituicao_id} não encontrada.",
            )

    senha_temp = auth_svc.gerar_senha_temporaria()
    senha_temp_hash = auth_svc.hash_senha(senha_temp)
    expira_em = auth_svc.calcular_expiracao_temp()

    voluntario = models.Voluntario(
        nome=payload.nome,
        telefone=payload.telefone,
        email=payload.email,
        instituicao_id=payload.instituicao_id,
        relato_original=payload.relato,
        habilidades=[],
        endereco_texto=payload.endereco,
        latitude=payload.latitude,
        longitude=payload.longitude,
        consentimento_lgpd=payload.consentimento_lgpd,
        senha_temp_hash=senha_temp_hash,
        senha_temp_expira_em=expira_em,
        precisa_trocar_senha=True,
    )
    db.add(voluntario)
    db.commit()
    db.refresh(voluntario)

    background_tasks.add_task(_enriquecer_voluntario, voluntario.id)

    return schemas.VoluntarioCadastroAceito(
        task_id=uuid.uuid4(),
        voluntario_id=voluntario.id,
        login_id=auth_svc.login_id_de(voluntario.id),
        senha_temporaria=senha_temp,
        senha_temp_expira_em=expira_em,
        mensagem=(
            "Cadastro recebido — enriquecimento em andamento. "
            "Use o login_id e a senha temporária acima para acessar o portal "
            "do voluntário. A senha é válida por 2 horas."
        ),
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
# GET /api/v1/voluntarios/verificar
# ---------------------------------------------------------------------------
@router.get(
    "/verificar",
    response_model=schemas.VoluntarioVerificacao,
    summary="Verificar duplicidade de cadastro",
    description=(
        "Consulta se já existe voluntário cadastrado com algum dos identificadores "
        "informados (telefone, nome ou email). Retorna apenas a indicação de "
        "duplicidade e o ID interno — NÃO expõe dados pessoais. Deve ser usado "
        "pelo agente antes de chamar `POST /api/v1/voluntarios`."
    ),
)
def verificar_voluntario(
    telefone: str | None = Query(None, min_length=8, max_length=40),
    nome: str | None = Query(None, min_length=2, max_length=200),
    email: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
):
    filtros = []
    if telefone:
        filtros.append(models.Voluntario.telefone == telefone)
    if email:
        filtros.append(models.Voluntario.email == email)
    if nome:
        filtros.append(models.Voluntario.nome.ilike(nome))

    if not filtros:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um dos parâmetros: telefone, nome ou email.",
        )

    existente = db.execute(
        select(models.Voluntario).where(or_(*filtros)).limit(1)
    ).scalar_one_or_none()

    if existente is None:
        return schemas.VoluntarioVerificacao(existe=False, campos_duplicados=[], voluntario_id=None)

    duplicados: list[str] = []
    if telefone and existente.telefone == telefone:
        duplicados.append("telefone")
    if email and existente.email == email:
        duplicados.append("email")
    if nome and existente.nome and existente.nome.lower() == nome.lower():
        duplicados.append("nome")

    return schemas.VoluntarioVerificacao(
        existe=True,
        campos_duplicados=duplicados,
        voluntario_id=existente.id,
    )


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
