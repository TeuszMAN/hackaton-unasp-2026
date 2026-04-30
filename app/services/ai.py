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


@dataclass
class ContextoJustificativa:
    """Dados resumidos passados para a IA gerar a frase de justificativa."""

    iniciais_voluntario: str
    habilidades_correspondentes: list[str]
    distancia_km: float | None
    reputacao: float | None
    nivel_urgencia: NivelUrgencia
    descricao_necessidade: str


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

    async def justificar_match(self, ctx: ContextoJustificativa) -> str:
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

    async def justificar_match(self, ctx: ContextoJustificativa) -> str:
        partes: list[str] = []
        if ctx.habilidades_correspondentes:
            skills = ", ".join(ctx.habilidades_correspondentes[:3])
            partes.append(f"tem {skills}")
        if ctx.distancia_km is not None:
            if ctx.distancia_km < 1:
                partes.append("está a menos de 1 km do local")
            else:
                partes.append(f"está a {ctx.distancia_km:.1f} km do local")
        if ctx.reputacao is not None and ctx.reputacao >= 4.0:
            partes.append(f"reputação alta ({ctx.reputacao:.1f}/5)")
        if not partes:
            return f"{ctx.iniciais_voluntario} é o candidato mais aderente disponível."
        return f"{ctx.iniciais_voluntario} foi escolhido(a) porque " + " e ".join(partes) + "."

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
    Integração com o IBM watsonx.ai (Granite).

    Usa o modelo Granite para:
      1. Extrair habilidades de voluntários a partir de relatos livres.
      2. Extrair requisitos de necessidades de crise (skills + urgência).
      3. Gerar justificativa em linguagem natural para cada match.

    Cada método faz fallback determinístico se as credenciais não estiverem
    configuradas ou se a API falhar.
    """

    def __init__(self) -> None:
        self._fallback = IAFallbackKeywords()
        self.api_key = os.getenv("WATSONX_API_KEY")
        self.project_id = os.getenv("WATSONX_PROJECT_ID")
        self.model_id = os.getenv("WATSONX_MODEL_ID", "ibm/granite-4-h-small")
        self.url = os.getenv(
            "WATSONX_URL",
            "https://us-south.ml.cloud.ibm.com",
        )
        self._codigos_taxonomia = [s["codigo"] for s in SKILLS_TAXONOMIA]
        if not self.api_key or not self.project_id:
            logger.warning(
                "WATSONX_API_KEY/WATSONX_PROJECT_ID não configurados — "
                "usando fallback determinístico."
            )

    # ---- Método interno: obter token IAM ---------------------------------
    async def _obter_token(self, client) -> str:
        """Obtém um access_token IBM IAM a partir da API key."""
        resp = await client.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self.api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ---- Método interno: chamar Granite ----------------------------------
    async def _chamar_granite(
        self,
        prompt: str,
        *,
        max_tokens: int = 200,
        stop_sequences: list[str] | None = None,
        system: str | None = None,
    ) -> str:
        """
        Envia prompt ao Granite via endpoint de chat e retorna o texto gerado.

        Usa `/ml/v1/text/chat` (formato OpenAI-compatible) — `/ml/v1/text/generation`
        está deprecated e modelos chat (granite-4) não respondem corretamente lá.
        """
        import httpx

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict = {
            "model_id": self.model_id,
            "project_id": self.project_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,  # determinístico (substitui o antigo decoding_method=greedy)
        }
        if stop_sequences:
            body["stop"] = stop_sequences

        async with httpx.AsyncClient(timeout=20.0) as client:
            access_token = await self._obter_token(client)
            resp = await client.post(
                f"{self.url}/ml/v1/text/chat?version=2024-05-01",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            return (message.get("content") or "").strip()

    # ---- Extração de habilidades do voluntário ---------------------------
    async def extrair_habilidades_voluntario(self, relato: str) -> ExtracaoVoluntario:
        if not self.api_key or not self.project_id:
            return await self._fallback.extrair_habilidades_voluntario(relato)
        try:
            codigos_str = "\n".join(f"  - {c}" for c in self._codigos_taxonomia)
            prompt = (
                "Você é um classificador de habilidades de voluntários para resposta a desastres.\n\n"
                "Códigos válidos de habilidades:\n"
                f"{codigos_str}\n\n"
                f"Relato do voluntário:\n\"{relato}\"\n\n"
                "Analise o relato acima e retorne APENAS um objeto JSON válido no formato:\n"
                "{\"habilidades\": [\"codigo1\", \"codigo2\"]}\n\n"
                "Use SOMENTE códigos da lista acima. Se nenhum se aplicar, retorne {\"habilidades\": []}.\n"
                "Responda APENAS com o JSON, sem explicações."
            )
            texto = await self._chamar_granite(prompt, max_tokens=150, stop_sequences=["\n\n"])
            import json
            # Tenta extrair JSON da resposta
            inicio = texto.find("{")
            fim = texto.rfind("}") + 1
            if inicio >= 0 and fim > inicio:
                parsed = json.loads(texto[inicio:fim])
                habilidades = [
                    h for h in parsed.get("habilidades", [])
                    if h in set(self._codigos_taxonomia)
                ]
                logger.info("[IAWatsonx] voluntário -> %s", habilidades)
                return ExtracaoVoluntario(habilidades=habilidades)
            raise ValueError(f"Resposta não contém JSON válido: {texto[:100]}")
        except Exception as e:
            logger.warning("Granite falhou para voluntário (%s) — usando fallback.", e)
            return await self._fallback.extrair_habilidades_voluntario(relato)

    # ---- Extração de requisitos de necessidade ---------------------------
    async def extrair_requisitos_necessidade(self, descricao: str) -> ExtracaoNecessidade:
        if not self.api_key or not self.project_id:
            return await self._fallback.extrair_requisitos_necessidade(descricao)
        try:
            codigos_str = "\n".join(f"  - {c}" for c in self._codigos_taxonomia)
            prompt = (
                "Você é um analisador de situações de crise para resposta a desastres.\n\n"
                "Códigos válidos de habilidades:\n"
                f"{codigos_str}\n\n"
                f"Descrição da crise:\n\"{descricao}\"\n\n"
                "Analise a descrição acima e retorne APENAS um objeto JSON válido no formato:\n"
                "{\"habilidades_requeridas\": [\"codigo1\", \"codigo2\"], \"nivel_urgencia\": \"medio\"}\n\n"
                "Regras:\n"
                "- Use SOMENTE códigos da lista acima para habilidades.\n"
                "- nivel_urgencia deve ser exatamente um de: baixo, medio, alto, critico\n"
                "- Avalie a urgência com base na gravidade descrita (risco de vida = critico, feridos = alto, etc.)\n"
                "Responda APENAS com o JSON, sem explicações."
            )
            texto = await self._chamar_granite(prompt, max_tokens=200, stop_sequences=["\n\n"])
            import json
            inicio = texto.find("{")
            fim = texto.rfind("}") + 1
            if inicio >= 0 and fim > inicio:
                parsed = json.loads(texto[inicio:fim])
                habilidades = [
                    h for h in parsed.get("habilidades_requeridas", [])
                    if h in set(self._codigos_taxonomia)
                ]
                urgencia_str = parsed.get("nivel_urgencia", "alto")
                try:
                    urgencia = NivelUrgencia(urgencia_str)
                except ValueError:
                    urgencia = NivelUrgencia.alto
                logger.info(
                    "[IAWatsonx] necessidade -> skills=%s urgencia=%s",
                    habilidades, urgencia,
                )
                return ExtracaoNecessidade(
                    habilidades_requeridas=habilidades,
                    nivel_urgencia=urgencia,
                )
            raise ValueError(f"Resposta não contém JSON válido: {texto[:100]}")
        except Exception as e:
            logger.warning("Granite falhou para necessidade (%s) — usando fallback.", e)
            return await self._fallback.extrair_requisitos_necessidade(descricao)

    # ---- Justificativa do match ------------------------------------------
    async def justificar_match(self, ctx: ContextoJustificativa) -> str:
        if not self.api_key or not self.project_id:
            return await self._fallback.justificar_match(ctx)
        try:
            return await self._gerar_justificativa_granite(ctx)
        except Exception as e:
            logger.warning("Granite falhou (%s) — usando fallback determinístico.", e)
            return await self._fallback.justificar_match(ctx)

    async def _gerar_justificativa_granite(self, ctx: ContextoJustificativa) -> str:
        """
        Chama o watsonx.ai (Granite) para gerar 1 frase explicando o match.

        Mantém a chamada simples: prompt curto, max_tokens baixo, temperatura
        baixa para garantir frases determinísticas e factuais.
        """
        skills = ", ".join(ctx.habilidades_correspondentes) or "habilidades gerais"
        dist = f"{ctx.distancia_km:.1f} km" if ctx.distancia_km is not None else "distância não informada"
        rep = f"{ctx.reputacao:.1f}/5" if ctx.reputacao is not None else "reputação não informada"
        descricao = (ctx.descricao_necessidade or "").strip()[:300]

        prompt = (
            "Você é um assistente que explica em UMA frase, em português do Brasil, "
            "por que um voluntário foi recomendado para um chamado de crise. "
            "Seja específico e factual. Não invente dados além dos fornecidos.\n\n"
            f"Chamado (urgência {ctx.nivel_urgencia.value}): {descricao}\n"
            f"Voluntário: {ctx.iniciais_voluntario}\n"
            f"Habilidades em comum: {skills}\n"
            f"Distância: {dist}\n"
            f"Reputação: {rep}\n\n"
            "Responda APENAS com a frase, sem prefixos como 'Resposta:'."
        )

        texto = await self._chamar_granite(prompt, max_tokens=80, stop_sequences=["\n\n"])
        return texto or await self._fallback.justificar_match(ctx)


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
