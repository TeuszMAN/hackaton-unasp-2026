"""
Router — Estatísticas agregadas (útil para pitch e dashboard).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/v1/estatisticas", tags=["Estatísticas"])


@router.get(
    "",
    response_model=schemas.EstatisticasOut,
    summary="Métricas agregadas da plataforma",
    description=(
        "Números de alto nível sobre voluntários, necessidades e vínculos. "
        "Ideal para o dashboard e para apresentar impacto no pitch."
    ),
)
def obter_estatisticas(db: Session = Depends(get_db)):
    total_vol = db.scalar(select(func.count(models.Voluntario.id))) or 0
    vol_disp = db.scalar(
        select(func.count(models.Voluntario.id)).where(
            models.Voluntario.disponibilidade == models.StatusVoluntario.disponivel
        )
    ) or 0
    total_nec = db.scalar(select(func.count(models.Necessidade.id))) or 0
    nec_abertas = db.scalar(
        select(func.count(models.Necessidade.id)).where(
            models.Necessidade.status == models.StatusNecessidade.aberta
        )
    ) or 0
    nec_criticas = db.scalar(
        select(func.count(models.Necessidade.id)).where(
            models.Necessidade.status == models.StatusNecessidade.aberta,
            models.Necessidade.nivel_urgencia == models.NivelUrgencia.critico,
        )
    ) or 0
    total_vinc = db.scalar(select(func.count(models.Vinculo.id))) or 0
    vinc_aceitos = db.scalar(
        select(func.count(models.Vinculo.id)).where(
            models.Vinculo.status == models.StatusVinculo.aceito
        )
    ) or 0
    vinc_concluidos = db.scalar(
        select(func.count(models.Vinculo.id)).where(
            models.Vinculo.status == models.StatusVinculo.concluido
        )
    ) or 0

    # Tempo médio até aceite (segundos → minutos)
    tempo_medio_min = db.scalar(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    models.Vinculo.aceito_em - models.Vinculo.proposto_em,
                )
            )
        ).where(models.Vinculo.aceito_em.is_not(None))
    )
    tempo_medio_min = (
        round(float(tempo_medio_min) / 60.0, 2) if tempo_medio_min is not None else None
    )

    reputacao_media = db.scalar(select(func.avg(models.Voluntario.reputacao)))
    reputacao_media = (
        round(float(reputacao_media), 2) if reputacao_media is not None else None
    )

    return schemas.EstatisticasOut(
        total_voluntarios=total_vol,
        voluntarios_disponiveis=vol_disp,
        total_necessidades=total_nec,
        necessidades_abertas=nec_abertas,
        necessidades_criticas_abertas=nec_criticas,
        total_vinculos=total_vinc,
        vinculos_aceitos=vinc_aceitos,
        vinculos_concluidos=vinc_concluidos,
        tempo_medio_ate_aceite_minutos=tempo_medio_min,
        reputacao_media=reputacao_media,
    )
