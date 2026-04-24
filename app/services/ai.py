"""
Interface de extração via IA (watsonx.ai / Granite).

Esta é a fronteira entre o backend (Mateus) e o motor de linguagem
(Vitor). A classe `IAExtracaoService` define o contrato; a
implementação padrão é um fallback determinístico baseado em keywords
contra a `SKILLS_TAXONOMIA`, suficiente para:

  1. Rodar o MVP/demo mesmo sem acesso ao watsonx.ai.
  2. Funcionar como fallback se a API do Granite estiver lenta ou fora.
  3. Servir como referência para Vitor implementar a versão "real".

**Para o Vitor plugar o watsonx.ai:**
  - Subclasse `IAExtracaoService` criando, por exemplo, `WatsonxAIService`.
  - Sobrescreva `extrair_habilidades_voluntario` e
    `extrair_requisitos_necessidade`.
  - Configure a variável de ambiente `IA_PROVIDER=watsonx` para que a
    factory `get_ia_service()` instancie sua classe.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass

from app.models import NivelUrgencia
from app.taxonomia import SKILLS_TAXONOMIA


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resultado estruturado
# ---------------------------------------------------------------------------
@dataclass
class ExtracaoVoluntario:
    habilidades: list[str]


@dataclass
class ExtracaoNecessidade:
    habilidades_requeridas: list[str]
    nivel_urgencia: NivelUrgencia


# ---------------------------------------------------------------------------
# Interface (contrato)
# ---------------------------------------------------------------------------
class IAExtracaoService:
    """
    Contrato de extração de informação estruturada a partir de relatos livres.

    Implementações concretas devem ser seguras para uso assíncrono via
    `await` — mesmo a implementação síncrona fallback é declarada `async`
    para uniformidade.
    """

    async def extrair_habilidades_voluntario(self, relato: str) -> ExtracaoVoluntario:
        raise NotImplementedError

    async def extrair_requisitos_necessidade(self, descricao: str) -> ExtracaoNecessidade:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _normalizar_texto(s: str) -> str:
    """Remove acentos e caixa para permitir match robusto."""
    nfkd = unicodedata.normalize("NFKD", s)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


_PALAVRAS_CRITICAS = [
    "critico", "emergencia", "urgente", "risco de vida", "imediato", "ilhado",
    "soterrado", "morrendo", "gravissimo",
]
_PALAVRAS_ALTO = [
    "urgente", "grave", "ferido", "machucado", "desabrigado", "enchente",
    "incendio", "deslizamento",
]
_PALAVRAS_MEDIO = [
    "atencao", "preciso", "precisamos", "necessitamos",
]


# ---------------------------------------------------------------------------
# Fallback determinístico (keyword-based)
# ---------------------------------------------------------------------------
class IAFallbackKeywords(IAExtracaoService):
    """
    Implementação de fallback que não depende de nenhum serviço externo.

    Para cada skill da taxonomia, verifica se algum dos seus sinônimos
    aparece no texto normalizado. Suficiente para demos e testes.
    """

    async def extrair_habilidades_voluntario(self, relato: str) -> ExtracaoVoluntario:
        habilidades = self._extrair_skills(relato)
        logger.info("[IAFallback] voluntário -> %s", habilidades)
        return ExtracaoVoluntario(habilidades=habilidades)

    async def extrair_requisitos_necessidade(self, descricao: str) -> ExtracaoNecessidade:
        habilidades = self._extrair_skills(descricao)
        urgencia = self._inferir_urgencia(descricao)
        logger.info(
            "[IAFallback] necessidade -> skills=%s urgencia=%s",
            habilidades,
            urgencia,
        )
        return ExtracaoNecessidade(
            habilidades_requeridas=habilidades,
            nivel_urgencia=urgencia,
        )

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def _extrair_skills(texto: str) -> list[str]:
        alvo = _normalizar_texto(texto)
        encontradas: list[str] = []
        for skill in SKILLS_TAXONOMIA:
            for sinonimo in skill["sinonimos"]:
                sinonimo_norm = _normalizar_texto(sinonimo)
                # match por palavra inteira quando o sinônimo é uma palavra só
                if " " in sinonimo_norm:
                    if sinonimo_norm in alvo:
                        encontradas.append(skill["codigo"])
                        break
                else:
                    pattern = r"\b" + re.escape(sinonimo_norm) + r"\b"
                    if re.search(pattern, alvo):
                        encontradas.append(skill["codigo"])
                        break
        # dedup preservando ordem
        vistos: set[str] = set()
        resultado: list[str] = []
        for c in encontradas:
            if c not in vistos:
                vistos.add(c)
                resultado.append(c)
        return resultado

    @staticmethod
    def _inferir_urgencia(texto: str) -> NivelUrgencia:
        alvo = _normalizar_texto(texto)
        if any(p in alvo for p in _PALAVRAS_CRITICAS):
            return NivelUrgencia.critico
        if any(p in alvo for p in _PALAVRAS_ALTO):
            return NivelUrgencia.alto
        if any(p in alvo for p in _PALAVRAS_MEDIO):
            return NivelUrgencia.medio
        return NivelUrgencia.medio  # padrão conservador


# ---------------------------------------------------------------------------
# Stub para implementação via watsonx.ai
# ---------------------------------------------------------------------------
class IAWatsonxService(IAExtracaoService):
    """
    Esqueleto da integração com o IBM watsonx.ai (Granite).

    **A ser implementado por Vitor.** Prompts sugeridos:

    VOLUNTÁRIO
    ----------
    "Dada a lista de códigos canônicos de habilidades abaixo, classifique
    este relato em um ou mais códigos. Retorne APENAS os códigos em JSON
    no formato {"habilidades": ["codigo1", ...]}. Códigos: ..."

    NECESSIDADE
    -----------
    "Dada a descrição de uma situação de crise, extraia:
      - habilidades necessárias (lista de códigos canônicos)
      - nível de urgência (baixo|medio|alto|critico)
    Responda em JSON no formato
    {"habilidades_requeridas": [...], "nivel_urgencia": "..."}"

    Enquanto não implementado, esta classe delega para o fallback.
    """

    def __init__(self) -> None:
        self._fallback = IAFallbackKeywords()
        self.api_key = os.getenv("WATSONX_API_KEY")
        self.project_id = os.getenv("WATSONX_PROJECT_ID")
        self.model_id = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")
        self.url = os.getenv(
            "WATSONX_URL",
            "https://us-south.ml.cloud.ibm.com",
        )
        if not self.api_key or not self.project_id:
            logger.warning(
                "WATSONX_API_KEY/WATSONX_PROJECT_ID não configurados — "
                "usando fallback determinístico."
            )

    async def extrair_habilidades_voluntario(self, relato: str) -> ExtracaoVoluntario:
        # TODO(Vitor): substituir pela chamada real ao watsonx.ai.
        return await self._fallback.extrair_habilidades_voluntario(relato)

    async def extrair_requisitos_necessidade(self, descricao: str) -> ExtracaoNecessidade:
        # TODO(Vitor): substituir pela chamada real ao watsonx.ai.
        return await self._fallback.extrair_requisitos_necessidade(descricao)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_cached: IAExtracaoService | None = None


def get_ia_service() -> IAExtracaoService:
    """
    Retorna a instância do serviço de IA conforme `IA_PROVIDER`.

    - `IA_PROVIDER=watsonx` → `IAWatsonxService`
    - qualquer outro valor (ou ausência) → `IAFallbackKeywords`
    """
    global _cached
    if _cached is not None:
        return _cached

    provider = os.getenv("IA_PROVIDER", "fallback").lower()
    if provider == "watsonx":
        _cached = IAWatsonxService()
    else:
        _cached = IAFallbackKeywords()
    logger.info("IA provider ativo: %s", _cached.__class__.__name__)
    return _cached
