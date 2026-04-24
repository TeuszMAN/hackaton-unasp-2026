"""
Router — Vínculos (matchmaking).

Fluxo:
  1. `POST /api/v1/vinculos` executa o algoritmo e cria registros de
     proposta de vínculo (status=`proposto`).
  2. O voluntário aceita (`.../aceitar`), recusa (`.../recusar`) ou
     o coordenador cancela.
  3. Após o atendimento, `.../concluir` marca como concluído.
  4. Feedback pós-atendimento realimenta a reputação do voluntário.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.matching import encontrar_matches


router = APIRouter(prefix="/api/v1/vinculos", tags=["Vínculos"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iniciais(nome: str) -> str:
    partes = [p for p in nome.split() if p]
    return ". ".join(p[0].upper() for p in partes) + "." if partes else ""


def _to_match_recomendado(vinculo: models.Vinculo) -> schemas.MatchRecomendado:
    v = vinculo.voluntario
    publico = schemas.VoluntarioPublico(
        id=v.id,
        iniciais=_iniciais(v.nome),
        habilidades=v.habilidades or [],
        reputacao=v.reputacao,
    )
    return schemas.MatchRecomendado(
        vinculo_id=vinculo.id,
        voluntario=publico,
        score_match=vinculo.score_match,
        habilidades_correspondentes=vinculo.habilidades_correspondentes or [],
        distancia_km=vinculo.distancia_km,
        status=vinculo.status,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos — executa matchmaking
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=schemas.MatchmakingResponse,
    summary="Executar matchmaking para uma necessidade",
    description=(
        "Roda o algoritmo de correspondência inteligente e cria registros de "
        "proposta de vínculo (status `proposto`) para os top-N voluntários "
        "mais aderentes. O score combina skill match, proximidade geográfica, "
        "reputação e disponibilidade recente (anti-burnout), com pesos "
        "ajustados conforme o nível de urgência da necessidade."
    ),
)
def executar_matchmaking(
    payload: schemas.VinculoCreate, db: Session = Depends(get_db)
):
    necessidade = db.get(models.Necessidade, payload.necessidade_id)
    if necessidade is None:
        raise HTTPException(status_code=404, detail="Necessidade não encontrada.")

    matches = encontrar_matches(db, necessidade, top_n=payload.top_n)

    # Antes de criar novos vínculos, invalida propostas prévias ainda não respondidas
    db.execute(
        update(models.Vinculo)
        .where(
            models.Vinculo.necessidade_id == necessidade.id,
            models.Vinculo.status == models.StatusVinculo.proposto,
        )
        .values(status=models.StatusVinculo.cancelado)
    )

    vinculos_criados: list[models.Vinculo] = []
    for r in matches:
        vinculo = models.Vinculo(
            necessidade_id=necessidade.id,
            voluntario_id=r.voluntario.id,
            status=models.StatusVinculo.proposto,
            score_match=r.score,
            habilidades_correspondentes=r.habilidades_correspondentes,
            distancia_km=r.distancia_km,
        )
        db.add(vinculo)
        vinculos_criados.append(vinculo)

    db.commit()
    for v in vinculos_criados:
        db.refresh(v)

    return schemas.MatchmakingResponse(
        necessidade_id=necessidade.id,
        nivel_urgencia=necessidade.nivel_urgencia,
        total_recomendados=len(vinculos_criados),
        recomendacoes=[_to_match_recomendado(v) for v in vinculos_criados],
    )


# ---------------------------------------------------------------------------
# GET /api/v1/vinculos/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{vinculo_id}",
    response_model=schemas.VinculoOut,
    summary="Consultar vínculo",
)
def obter_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    return v


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/aceitar
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/aceitar",
    response_model=schemas.VinculoOut,
    summary="Voluntário aceita o vínculo",
    description=(
        "Quando aceito, a necessidade transita para `em_atendimento` e o "
        "voluntário para `em_missao`. Este endpoint expõe o vínculo completo "
        "(inclusive contato) para a instituição consultar."
    ),
)
def aceitar_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    vinculo = db.get(models.Vinculo, vinculo_id)
    if vinculo is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if vinculo.status != models.StatusVinculo.proposto:
        raise HTTPException(
            status_code=409,
            detail=f"Vínculo em status '{vinculo.status.value}' não pode ser aceito.",
        )

    agora = datetime.now(timezone.utc)
    vinculo.status = models.StatusVinculo.aceito
    vinculo.aceito_em = agora

    vinculo.voluntario.disponibilidade = models.StatusVoluntario.em_missao
    vinculo.necessidade.status = models.StatusNecessidade.em_atendimento

    # Cancela outras propostas concorrentes para o mesmo voluntário
    db.execute(
        update(models.Vinculo)
        .where(
            models.Vinculo.voluntario_id == vinculo.voluntario_id,
            models.Vinculo.id != vinculo.id,
            models.Vinculo.status == models.StatusVinculo.proposto,
        )
        .values(status=models.StatusVinculo.cancelado)
    )

    db.commit()
    db.refresh(vinculo)
    return vinculo


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/recusar
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/recusar",
    response_model=schemas.VinculoOut,
    summary="Voluntário recusa o vínculo",
)
def recusar_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if v.status != models.StatusVinculo.proposto:
        raise HTTPException(
            status_code=409,
            detail=f"Vínculo em status '{v.status.value}' não pode ser recusado.",
        )
    v.status = models.StatusVinculo.recusado
    db.commit()
    db.refresh(v)
    return v


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/concluir
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/concluir",
    response_model=schemas.VinculoOut,
    summary="Registrar conclusão do atendimento",
    description=(
        "Marca o vínculo como concluído e libera o voluntário (volta para "
        "`disponivel`). A necessidade é marcada como `resolvida`."
    ),
)
def concluir_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if v.status not in (models.StatusVinculo.aceito, models.StatusVinculo.em_atendimento):
        raise HTTPException(
            status_code=409,
            detail=f"Vínculo em status '{v.status.value}' não pode ser concluído.",
        )

    agora = datetime.now(timezone.utc)
    v.status = models.StatusVinculo.concluido
    v.concluido_em = agora

    v.voluntario.disponibilidade = models.StatusVoluntario.disponivel
    v.voluntario.ultima_missao_em = agora
    v.necessidade.status = models.StatusNecessidade.resolvida

    db.commit()
    db.refresh(v)
    return v


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/feedback
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/feedback",
    response_model=schemas.FeedbackOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar feedback pós-atendimento",
    description=(
        "Fecha o loop agêntico: o feedback ajusta a reputação do voluntário "
        "via média móvel simples, realimentando o ranking em futuros matches."
    ),
)
def registrar_feedback(
    vinculo_id: uuid.UUID,
    payload: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if v.feedback is not None:
        raise HTTPException(status_code=409, detail="Feedback já registrado para este vínculo.")

    fb = models.Feedback(
        vinculo_id=v.id,
        voluntario_compareceu=payload.voluntario_compareceu,
        skill_adequada=payload.skill_adequada,
        nota=payload.nota,
        comentario=payload.comentario,
    )
    db.add(fb)

    # Atualiza reputação — média móvel simples ponderada
    voluntario = v.voluntario
    atual = voluntario.reputacao or 3.0
    voluntario.reputacao = round((atual * 0.7) + (payload.nota * 0.3), 2)

    db.commit()
    db.refresh(fb)
    return fb
