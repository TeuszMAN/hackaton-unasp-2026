"""
Router — Instituições.

Endpoints para cadastro, consulta e atualização de instituições parceiras.
Instituições são entidades que registram necessidades de crise na plataforma.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/v1/instituicoes", tags=["Instituições"])


# ---------------------------------------------------------------------------
# POST /api/v1/instituicoes
# ---------------------------------------------------------------------------
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.InstituicaoOut,
    summary="Cadastrar instituição",
    description="Registra uma nova instituição parceira na plataforma.",
)
def cadastrar_instituicao(
    payload: schemas.InstituicaoCreate,
    db: Session = Depends(get_db),
):
    if payload.cnpj:
        existente = db.execute(
            select(models.Instituicao).where(models.Instituicao.cnpj == payload.cnpj)
        ).scalar_one_or_none()
        if existente:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma instituição cadastrada com este CNPJ.",
            )

    instituicao = models.Instituicao(
        nome=payload.nome,
        cnpj=payload.cnpj,
        contato=payload.contato,
    )
    db.add(instituicao)
    db.commit()
    db.refresh(instituicao)
    return instituicao


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
    verificada: bool | None = Query(None, description="Filtra pelo status de verificação."),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.Instituicao)
    if verificada is not None:
        stmt = stmt.where(models.Instituicao.verificada == verificada)
    stmt = stmt.limit(limit).order_by(models.Instituicao.criado_em.desc())
    return list(db.execute(stmt).scalars().all())


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
    description="Atualiza parcialmente os dados de uma instituição, incluindo seu status de verificação.",
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

    if "cnpj" in data and data["cnpj"] is not None:
        conflito = db.execute(
            select(models.Instituicao).where(
                models.Instituicao.cnpj == data["cnpj"],
                models.Instituicao.id != instituicao_id,
            )
        ).scalar_one_or_none()
        if conflito:
            raise HTTPException(
                status_code=409,
                detail="Já existe outra instituição cadastrada com este CNPJ.",
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
    description="Remove uma instituição. Necessidades vinculadas são excluídas em cascata (cascade delete).",
)
def remover_instituicao(instituicao_id: uuid.UUID, db: Session = Depends(get_db)):
    inst = db.get(models.Instituicao, instituicao_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    db.delete(inst)
    db.commit()
