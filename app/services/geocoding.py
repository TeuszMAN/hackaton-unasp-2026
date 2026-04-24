"""
Geocodificação simples via OpenStreetMap Nominatim.

Não depende de chave de API, o que é ideal para o hackathon. Em
produção, trocar por um provedor comercial (Google Maps / HERE /
IBM Cloud).
"""

from __future__ import annotations

import logging

import httpx


logger = logging.getLogger(__name__)


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "voluntariado-inteligente-hackathon/0.2 (contato@hackathon.local)"
TIMEOUT_SEG = 5.0


async def geocodificar(endereco: str) -> tuple[float, float] | None:
    """
    Converte um endereço textual em (latitude, longitude).

    Retorna `None` em qualquer falha — chamadores devem tratar esse caso
    e prosseguir sem coordenadas, apenas com menor precisão de matching.
    """
    if not endereco or len(endereco.strip()) < 3:
        return None

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEG) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": endereco, "format": "json", "limit": 1, "countrycodes": "br"},
                headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"},
            )
            response.raise_for_status()
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:  # noqa: BLE001 — geocoding é best-effort
        logger.warning("Falha ao geocodificar '%s': %s", endereco, exc)

    return None
