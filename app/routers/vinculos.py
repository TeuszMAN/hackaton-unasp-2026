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
from app.services.ai import (
    ContextoJustificativa,
    IAFallbackKeywords,
    get_ia_service,
)
from app.services.matching import MatchResult, encontrar_matches


router = APIRouter(prefix="/api/v1/vinculos", tags=["Vínculos"])

# Fallback determinístico reusado quando a IA falha — instanciado uma vez para
# evitar custo de inicialização por requisição. Garante que `justificativa`
# nunca seja None quando o LLM cair, preservando a UX do painel.
_fallback_justificativa = IAFallbackKeywords()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iniciais(nome: str) -> str:
    partes = [p for p in nome.split() if p]
    return ". ".join(p[0].upper() for p in partes) + "." if partes else ""


def _to_match_recomendado(
    vinculo: models.Vinculo,
    justificativa: str | None = None,
    recomendado: bool = False,
) -> schemas.MatchRecomendado:
    v = vinculo.voluntario
    publico = schemas.VoluntarioPublico(
        id=v.id,
        nome=v.nome,
        iniciais=_iniciais(v.nome),
        habilidades=v.habilidades or [],
        reputacao=v.reputacao,
    )
    distancia_m = (
        int(round(vinculo.distancia_km * 1000)) if vinculo.distancia_km is not None else None
    )
    return schemas.MatchRecomendado(
        vinculo_id=vinculo.id,
        voluntario=publico,
        score_match=vinculo.score_match,
        habilidades_correspondentes=vinculo.habilidades_correspondentes or [],
        distancia_km=vinculo.distancia_km,
        distancia_m=distancia_m,
        recomendado=recomendado,
        status=vinculo.status,
        justificativa=justificativa,
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
async def executar_matchmaking(
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
            models.Vinculo.status.in_(
                [
                    models.StatusVinculo.aguardando_aprovacao,
                    models.StatusVinculo.proposto,
                ]
            ),
        )
        .values(status=models.StatusVinculo.cancelado)
    )

    vinculos_criados: list[tuple[models.Vinculo, MatchResult]] = []
    for r in matches:
        vinculo = models.Vinculo(
            necessidade_id=necessidade.id,
            voluntario_id=r.voluntario.id,
            status=models.StatusVinculo.aguardando_aprovacao,
            score_match=r.score,
            habilidades_correspondentes=r.habilidades_correspondentes,
            distancia_km=r.distancia_km,
        )
        db.add(vinculo)
        vinculos_criados.append((vinculo, r))

    db.commit()
    for v, _ in vinculos_criados:
        db.refresh(v)

    # Identifica o vínculo "recomendado" — o de menor distância (entre os que têm coordenadas).
    com_distancia = [v for v, _ in vinculos_criados if v.distancia_km is not None]
    vinculo_recomendado_id = (
        min(com_distancia, key=lambda v: v.distancia_km).id if com_distancia else None
    )

    # Justificativa via IA (Granite no provider watsonx, fallback determinístico caso contrário).
    ia = get_ia_service()
    recomendacoes: list[schemas.MatchRecomendado] = []
    for vinculo, resultado in vinculos_criados:
        ctx = ContextoJustificativa(
            iniciais_voluntario=_iniciais(vinculo.voluntario.nome),
            habilidades_correspondentes=resultado.habilidades_correspondentes,
            distancia_km=resultado.distancia_km,
            reputacao=vinculo.voluntario.reputacao,
            nivel_urgencia=necessidade.nivel_urgencia,
            descricao_necessidade=necessidade.descricao_crise or "",
        )
        # Cadeia de fallback em três camadas:
        #   1. Provedor configurado (watsonx Granite ou stub determinístico)
        #   2. Fallback de palavras-chave local (sempre disponível, sem rede)
        #   3. String fixa — garantia última de UX se tudo cair
        justificativa: str | None = None
        try:
            justificativa = await ia.justificar_match(ctx)
        except Exception:
            try:
                justificativa = await _fallback_justificativa.justificar_match(ctx)
            except Exception:
                justificativa = (
                    "Recomendado pelo algoritmo com base em skills, "
                    "proximidade e reputação."
                )
        recomendacoes.append(
            _to_match_recomendado(
                vinculo,
                justificativa,
                recomendado=(vinculo.id == vinculo_recomendado_id),
            )
        )

    return schemas.MatchmakingResponse(
        necessidade_id=necessidade.id,
        nivel_urgencia=necessidade.nivel_urgencia,
        total_recomendados=len(vinculos_criados),
        recomendacoes=recomendacoes,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/vinculos/pendentes — caixa de aprovação institucional
# ---------------------------------------------------------------------------
@router.get(
    "/pendentes",
    response_model=list[schemas.GrupoAprovacao],
    summary="Listar vínculos aguardando aprovação institucional",
    description=(
        "Retorna os vínculos com status `aguardando_aprovacao`, agrupados por "
        "necessidade. Cada grupo lista os candidatos sugeridos pelo algoritmo, "
        "com o de menor distância marcado como `recomendado`. É a fonte da "
        "caixa de aprovação no painel."
    ),
)
def listar_pendentes(db: Session = Depends(get_db)):
    from sqlalchemy import select as _select

    stmt = _select(models.Vinculo).where(
        models.Vinculo.status == models.StatusVinculo.aguardando_aprovacao
    )
    vinculos = list(db.execute(stmt).scalars().all())
    if not vinculos:
        return []

    grupos: dict[uuid.UUID, list[models.Vinculo]] = {}
    for v in vinculos:
        grupos.setdefault(v.necessidade_id, []).append(v)

    resposta: list[schemas.GrupoAprovacao] = []
    for necessidade_id, lista in grupos.items():
        necessidade = db.get(models.Necessidade, necessidade_id)
        if necessidade is None:
            continue
        com_dist = [v for v in lista if v.distancia_km is not None]
        rec_id = min(com_dist, key=lambda v: v.distancia_km).id if com_dist else None
        candidatos = [
            _to_match_recomendado(v, justificativa=None, recomendado=(v.id == rec_id))
            for v in lista
        ]
        resposta.append(
            schemas.GrupoAprovacao(
                necessidade=schemas.NecessidadeResumo.model_validate(necessidade),
                candidatos=candidatos,
            )
        )
    return resposta


# ---------------------------------------------------------------------------
# GET /api/v1/vinculos/voluntario/{voluntario_id}
# ---------------------------------------------------------------------------
@router.get(
    "/voluntario/{voluntario_id}",
    response_model=list[schemas.VinculoOut],
    summary="Listar vínculos de um voluntário",
    description="Retorna todos os vínculos associados a um voluntário específico.",
)
def listar_vinculos_voluntario(voluntario_id: uuid.UUID, db: Session = Depends(get_db)):
    from sqlalchemy import select as _select

    stmt = _select(models.Vinculo).where(models.Vinculo.voluntario_id == voluntario_id)
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/aprovar — instituição aprova candidato
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/aprovar",
    response_model=schemas.VinculoOut,
    summary="Instituição aprova candidato (libera para o voluntário decidir)",
    description=(
        "Move o vínculo de `aguardando_aprovacao` para `proposto`. Os demais "
        "candidatos da mesma necessidade ainda em `aguardando_aprovacao` são "
        "automaticamente cancelados — só o aprovado é acionado."
    ),
)
def aprovar_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if v.status != models.StatusVinculo.aguardando_aprovacao:
        raise HTTPException(
            status_code=409,
            detail=f"Vínculo em status '{v.status.value}' não pode ser aprovado.",
        )

    v.status = models.StatusVinculo.proposto

    # Cancela os demais candidatos da mesma necessidade que estavam aguardando
    db.execute(
        update(models.Vinculo)
        .where(
            models.Vinculo.necessidade_id == v.necessidade_id,
            models.Vinculo.id != v.id,
            models.Vinculo.status == models.StatusVinculo.aguardando_aprovacao,
        )
        .values(status=models.StatusVinculo.cancelado)
    )

    db.commit()
    db.refresh(v)
    return v


# ---------------------------------------------------------------------------
# POST /api/v1/vinculos/{id}/rejeitar — instituição rejeita candidato
# ---------------------------------------------------------------------------
@router.post(
    "/{vinculo_id}/rejeitar",
    response_model=schemas.VinculoOut,
    summary="Instituição rejeita candidato sugerido",
    description=(
        "Marca um candidato como `rejeitado` (não chega ao voluntário). Não "
        "afeta os demais candidatos da mesma necessidade."
    ),
)
def rejeitar_vinculo(vinculo_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.get(models.Vinculo, vinculo_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    if v.status != models.StatusVinculo.aguardando_aprovacao:
        raise HTTPException(
            status_code=409,
            detail=f"Vínculo em status '{v.status.value}' não pode ser rejeitado.",
        )
    v.status = models.StatusVinculo.rejeitado
    db.commit()
    db.refresh(v)
    return v


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