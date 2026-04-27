"""
Router — Instituições.

CRUD de instituições parceiras que abrem chamados na plataforma.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/v1/instituicoes", tags=["Instituições"])


# ---------------------------------------------------------------------------
# POST /api/v1/instituicoes
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=schemas.InstituicaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar instituição",
    description=(
        "Cria uma nova instituição parceira. Retorna 409 se já existe instituição "
        "com o mesmo CNPJ."
    ),
)
def cadastrar_instituicao(
    payload: schemas.InstituicaoCreate,
    db: Session = Depends(get_db),
):
    if payload.cnpj:
        existente = db.execute(
            select(models.Instituicao).where(models.Instituicao.cnpj == payload.cnpj)
        ).scalar_one_or_none()
        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Instituição já cadastrada com este CNPJ. "
                    f"Utilize o ID existente: {existente.id}"
                ),
            )

    inst = models.Instituicao(
        nome=payload.nome,
        cnpj=payload.cnpj,
        regiao=payload.regiao,
        contato=payload.contato,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


# ---------------------------------------------------------------------------
# GET /api/v1/instituicoes
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=list[schemas.InstituicaoOut],
    summary="Listar instituições",
    description="Lista instituições cadastradas com filtros opcionais.",
)
def listar_instituicoes(
    verificada: bool | None = Query(None, description="Filtra por status de verificação."),
    regiao: str | None = Query(
        None,
        max_length=120,
        description="Filtra instituições pela região (case-insensitive, match exato ou parcial).",
    ),
    busca: str | None = Query(
        None,
        min_length=2,
        max_length=200,
        description="Busca textual em nome ou CNPJ (case-insensitive).",
    ),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.Instituicao)
    if verificada is not None:
        stmt = stmt.where(models.Instituicao.verificada == verificada)
    if regiao:
        stmt = stmt.where(models.Instituicao.regiao.ilike(f"%{regiao}%"))
    if busca:
        termo = f"%{busca}%"
        stmt = stmt.where(
            or_(
                models.Instituicao.nome.ilike(termo),
                models.Instituicao.cnpj.ilike(termo),
            )
        )
    stmt = stmt.order_by(models.Instituicao.criado_em.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# GET /api/v1/instituicoes/regioes — para o agente listar regiões disponíveis
# ---------------------------------------------------------------------------
@router.get(
    "/regioes",
    response_model=list[schemas.RegiaoOut],
    summary="Listar regiões com instituições cadastradas",
    description=(
        "Retorna a lista distinta de regiões e quantas instituições há em "
        "cada uma. O agente do Watson usa este endpoint para perguntar ao "
        "voluntário em qual região ele deseja atuar antes de listar as "
        "instituições disponíveis."
    ),
)
def listar_regioes(db: Session = Depends(get_db)):
    stmt = (
        select(models.Instituicao.regiao, func.count(models.Instituicao.id))
        .where(models.Instituicao.regiao.is_not(None))
        .group_by(models.Instituicao.regiao)
        .order_by(models.Instituicao.regiao)
    )
    rows = db.execute(stmt).all()
    return [schemas.RegiaoOut(regiao=r, total_instituicoes=total) for r, total in rows]


# ---------------------------------------------------------------------------
# GET /api/v1/instituicoes/verificar
# ---------------------------------------------------------------------------
@router.get(
    "/verificar",
    response_model=schemas.InstituicaoVerificacao,
    summary="Verificar duplicidade de cadastro de instituição",
    description=(
        "Consulta se já existe instituição cadastrada com o CNPJ informado. "
        "Retorna apenas a indicação de duplicidade e o ID interno — NÃO expõe "
        "dados de contato. Deve ser usado pelo agente antes de chamar "
        "`POST /api/v1/instituicoes`."
    ),
)
def verificar_instituicao(
    cnpj: str = Query(..., min_length=14, max_length=20, description="CNPJ da instituição."),
    db: Session = Depends(get_db),
):
    existente = db.execute(
        select(models.Instituicao).where(models.Instituicao.cnpj == cnpj)
    ).scalar_one_or_none()

    if existente is None:
        return schemas.InstituicaoVerificacao(existe=False, instituicao_id=None)

    return schemas.InstituicaoVerificacao(
        existe=True,
        instituicao_id=existente.id,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/instituicoes/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{instituicao_id}",
    response_model=schemas.InstituicaoOut,
    summary="Consultar instituição",
)
def obter_instituicao(instituicao_id: uuid.UUID, db: Session = Depends(get_db)):
    inst = db.get(models.Instituicao, instituicao_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    return inst


# ---------------------------------------------------------------------------
# PATCH /api/v1/instituicoes/{id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{instituicao_id}",
    response_model=schemas.InstituicaoOut,
    summary="Atualizar instituição",
    description=(
        "Atualiza parcialmente os dados de uma instituição. Útil também para "
        "marcar como `verificada=true` após validação manual."
    ),
)
def atualizar_instituicao(
    instituicao_id: uuid.UUID,
    payload: schemas.InstituicaoUpdate,
    db: Session = Depends(get_db),
):
    inst = db.get(models.Instituicao, instituicao_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")

    data = payload.model_dump(exclude_unset=True)

    novo_cnpj = data.get("cnpj")
    if novo_cnpj and novo_cnpj != inst.cnpj:
        existente = db.execute(
            select(models.Instituicao).where(models.Instituicao.cnpj == novo_cnpj)
        ).scalar_one_or_none()
        if existente is not None and existente.id != instituicao_id:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe outra instituição com este CNPJ (id={existente.id}).",
            )

    for campo, valor in data.items():
        setattr(inst, campo, valor)
    db.commit()
    db.refresh(inst)
    return inst


# ---------------------------------------------------------------------------
# DELETE /api/v1/instituicoes/{id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{instituicao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover instituição",
    description=(
        "Remove uma instituição. Atenção: a remoção propaga em cascata para "
        "as necessidades vinculadas (conforme definido no model)."
    ),
)
def remover_instituicao(instituicao_id: uuid.UUID, db: Session = Depends(get_db)):
    inst = db.get(models.Instituicao, instituicao_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    db.delete(inst)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# GET /api/v1/instituicoes/{id}/necessidades
# ---------------------------------------------------------------------------
@router.get(
    "/{instituicao_id}/necessidades",
    response_model=list[schemas.NecessidadeOut],
    summary="Listar chamados de uma instituição",
    description="Retorna todos os chamados (necessidades) registrados pela instituição informada.",
)
def listar_necessidades_da_instituicao(
    instituicao_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    inst = db.get(models.Instituicao, instituicao_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")

    stmt = (
        select(models.Necessidade)
        .where(models.Necessidade.instituicao_id == instituicao_id)
        .order_by(models.Necessidade.criado_em.desc())
    )
    return list(db.execute(stmt).scalars().all())
