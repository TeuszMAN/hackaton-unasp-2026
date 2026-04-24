"""
Algoritmo de matchmaking.

Score composto, com pesos ajustáveis por nível de urgência:

    score = α · skill_match + β · proximidade + γ · reputacao + δ · disponibilidade

Ver `ARCHITECTURE.md` seção 7 para a tabela de pesos e justificativas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.models import NivelUrgencia, StatusVoluntario


# ---------------------------------------------------------------------------
# Pesos por urgência (α, β, γ, δ)
# ---------------------------------------------------------------------------
PESOS_POR_URGENCIA: dict[NivelUrgencia, dict[str, float]] = {
    NivelUrgencia.critico: {"alpha": 0.25, "beta": 0.50, "gamma": 0.15, "delta": 0.10},
    NivelUrgencia.alto:    {"alpha": 0.35, "beta": 0.35, "gamma": 0.20, "delta": 0.10},
    NivelUrgencia.medio:   {"alpha": 0.45, "beta": 0.25, "gamma": 0.20, "delta": 0.10},
    NivelUrgencia.baixo:   {"alpha": 0.50, "beta": 0.20, "gamma": 0.20, "delta": 0.10},
}

RAIO_MAXIMO_KM = 50.0  # acima disso, proximidade = 0
JANELA_FADIGA_HORAS = 72.0  # voluntário acionado nas últimas 72h sofre penalização


# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------
@dataclass
class MatchResult:
    voluntario: models.Voluntario
    score: float
    distancia_km: float | None
    skill_match_pct: float
    habilidades_correspondentes: list[str]


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em km entre dois pontos (fórmula de Haversine)."""
    R = 6371.0
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Score individual
# ---------------------------------------------------------------------------
def calcular_score(
    voluntario: models.Voluntario, necessidade: models.Necessidade
) -> MatchResult:
    urgencia = necessidade.nivel_urgencia
    pesos = PESOS_POR_URGENCIA.get(urgencia, PESOS_POR_URGENCIA[NivelUrgencia.alto])

    # --- Skill match ---------------------------------------------------
    hab_v = set(voluntario.habilidades or [])
    hab_n = set(necessidade.habilidades_requeridas or [])
    correspondentes = sorted(hab_v & hab_n)
    skill_match_pct = (len(correspondentes) / len(hab_n)) if hab_n else 0.0

    # --- Proximidade ---------------------------------------------------
    if (
        voluntario.latitude is not None
        and voluntario.longitude is not None
        and necessidade.latitude is not None
        and necessidade.longitude is not None
    ):
        distancia_km = haversine_km(
            voluntario.latitude,
            voluntario.longitude,
            necessidade.latitude,
            necessidade.longitude,
        )
        proximidade = max(0.0, 1.0 - distancia_km / RAIO_MAXIMO_KM)
    else:
        distancia_km = None
        proximidade = 0.5  # sinal neutro quando faltam coordenadas

    # --- Reputação -----------------------------------------------------
    reputacao_norm = max(0.0, min(1.0, (voluntario.reputacao or 3.0) / 5.0))

    # --- Disponibilidade / anti-burnout --------------------------------
    if voluntario.ultima_missao_em:
        ultima = voluntario.ultima_missao_em
        if ultima.tzinfo is None:
            ultima = ultima.replace(tzinfo=timezone.utc)
        horas = (datetime.now(timezone.utc) - ultima).total_seconds() / 3600.0
        disponibilidade = min(1.0, horas / JANELA_FADIGA_HORAS)
    else:
        disponibilidade = 1.0

    score = (
        pesos["alpha"] * skill_match_pct
        + pesos["beta"] * proximidade
        + pesos["gamma"] * reputacao_norm
        + pesos["delta"] * disponibilidade
    )

    return MatchResult(
        voluntario=voluntario,
        score=round(score, 4),
        distancia_km=round(distancia_km, 2) if distancia_km is not None else None,
        skill_match_pct=round(skill_match_pct, 4),
        habilidades_correspondentes=correspondentes,
    )


# ---------------------------------------------------------------------------
# Consulta inteligente
# ---------------------------------------------------------------------------
def encontrar_matches(
    db: Session, necessidade: models.Necessidade, top_n: int = 5
) -> list[MatchResult]:
    """
    Retorna os `top_n` voluntários mais aderentes à necessidade.

    Regras de filtro rígido (pré-score):
      - voluntário precisa estar `disponivel`
      - precisa ter consentimento LGPD registrado
      - precisa ter ao menos uma habilidade em comum com a necessidade
    """
    requeridas = set(necessidade.habilidades_requeridas or [])

    stmt = select(models.Voluntario).where(
        models.Voluntario.disponibilidade == StatusVoluntario.disponivel,
        models.Voluntario.consentimento_lgpd.is_(True),
    )
    candidatos = db.execute(stmt).scalars().all()

    resultados: list[MatchResult] = []
    for v in candidatos:
        if not v.habilidades:
            continue
        if requeridas and not (set(v.habilidades) & requeridas):
            continue
        resultados.append(calcular_score(v, necessidade))

    resultados.sort(key=lambda r: r.score, reverse=True)
    return resultados[:top_n]
