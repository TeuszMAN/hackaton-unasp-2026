"""
API de Orquestração de Voluntariado Inteligente para Situações de Crise.

Esta API conecta instituições que precisam de ajuda urgente com voluntários
qualificados, utilizando correspondência baseada em habilidades (skill-based
volunteering). Projetada para ser consumida como Skill pelo IBM watsonx
Orchestrate.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class NivelUrgencia(str, Enum):
    """Nível de urgência da necessidade emergencial."""

    baixo = "baixo"
    medio = "medio"
    alto = "alto"
    critico = "critico"


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------
class NecessidadeEmergencia(BaseModel):
    """
    Representa uma necessidade emergencial reportada por uma instituição.

    Contém as informações necessárias para que o sistema encontre
    voluntários com as habilidades adequadas na região da crise.
    """

    descricao_crise: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description=(
            "Descrição detalhada da situação de crise enfrentada pela "
            "instituição, incluindo o contexto e a natureza do problema."
        ),
        json_schema_extra={"example": "Enchente atingiu abrigo comunitário no bairro Vila Nova. Necessidade urgente de equipe médica e resgate."},
    )
    habilidades_requeridas: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Lista de habilidades profissionais ou técnicas necessárias "
            "para atender a emergência. Ex.: 'primeiros_socorros', "
            "'resgate_aquatico', 'engenharia_civil'."
        ),
        json_schema_extra={"example": ["primeiros_socorros", "resgate_aquatico"]},
    )
    localizacao: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description=(
            "Endereço ou coordenadas geográficas do local da crise. "
            "Pode ser um endereço textual ou coordenadas no formato 'lat,lon'."
        ),
        json_schema_extra={"example": "Rua das Flores, 123 - Vila Nova, São Paulo - SP"},
    )
    nivel_urgencia: NivelUrgencia = Field(
        ...,
        description=(
            "Nível de urgência da situação. Valores possíveis: "
            "'baixo', 'medio', 'alto', 'critico'."
        ),
        json_schema_extra={"example": "critico"},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "descricao_crise": "Enchente atingiu abrigo comunitário no bairro Vila Nova. Necessidade urgente de equipe médica e resgate.",
                    "habilidades_requeridas": ["primeiros_socorros", "resgate_aquatico"],
                    "localizacao": "Rua das Flores, 123 - Vila Nova, São Paulo - SP",
                    "nivel_urgencia": "critico",
                }
            ]
        }
    }


class VoluntarioMatch(BaseModel):
    """
    Representa um voluntário compatível encontrado pelo sistema de
    correspondência de habilidades.

    Retornado como resultado da orquestração, contém os dados de contato
    e a habilidade que motivou a seleção deste voluntário.
    """

    nome: str = Field(
        ...,
        description="Nome completo do voluntário disponível para atendimento.",
        json_schema_extra={"example": "Ana Carolina Silva"},
    )
    telefone: str = Field(
        ...,
        description=(
            "Número de telefone do voluntário para contato imediato, "
            "incluindo DDD. Formato: (XX) XXXXX-XXXX."
        ),
        json_schema_extra={"example": "(11) 98765-4321"},
    )
    habilidade_correspondente: str = Field(
        ...,
        description=(
            "Habilidade do voluntário que corresponde a uma das "
            "habilidades requeridas na solicitação de emergência."
        ),
        json_schema_extra={"example": "primeiros_socorros"},
    )
    distancia_km: float = Field(
        ...,
        ge=0,
        description=(
            "Distância em quilômetros entre o voluntário e o local "
            "da crise. Quanto menor, maior a prioridade."
        ),
        json_schema_extra={"example": 2.5},
    )


class OrquestracaoResponse(BaseModel):
    """Resposta completa da orquestração de resgate."""

    total_voluntarios: int = Field(
        ...,
        description="Quantidade total de voluntários compatíveis encontrados.",
    )
    voluntarios: list[VoluntarioMatch] = Field(
        ...,
        description="Lista de voluntários compatíveis ordenados por proximidade.",
    )


# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API de Voluntariado Inteligente para Crises",
    description=(
        "API de orquestração que conecta instituições em situação de crise "
        "com voluntários qualificados, utilizando correspondência baseada em "
        "habilidades (skill-based volunteering). Projetada para integração "
        "com o IBM watsonx Orchestrate como Skill."
    ),
    version="0.1.0",
    contact={
        "name": "Equipe Hackathon UNASP 2026",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Verificação de saúde da API.",
        },
        {
            "name": "Orquestração",
            "description": (
                "Endpoints de orquestração de voluntários para "
                "atendimento a emergências."
            ),
        },
    ],
)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.get(
    "/",
    tags=["Health"],
    summary="Health Check",
    description="Verifica se a API está online e operacional.",
    response_description="Status de saúde da API.",
)
def health_check():
    """Retorna o status de saúde da API."""
    return {"status": "ok", "service": "voluntariado-inteligente-api", "version": "0.1.0"}


@app.post(
    "/api/v1/orquestrar-resgate",
    tags=["Orquestração"],
    summary="Orquestrar resgate com voluntários",
    description=(
        "Recebe uma necessidade emergencial descrevendo a crise, as habilidades "
        "requeridas, a localização e o nível de urgência. Retorna uma lista de "
        "voluntários compatíveis ordenados por proximidade geográfica. "
        "Atualmente utiliza dados mockados para validação do contrato OpenAPI."
    ),
    response_description="Lista de voluntários compatíveis com as habilidades requeridas.",
    response_model=OrquestracaoResponse,
)
def orquestrar_resgate(necessidade: NecessidadeEmergencia):
    """
    Orquestra o resgate conectando a necessidade emergencial com
    voluntários qualificados disponíveis na região.

    O sistema analisa as habilidades requeridas pela instituição e
    realiza a correspondência com voluntários cadastrados, priorizando
    por proximidade geográfica.

    **Dados mockados** — esta rota retorna dados fictícios para
    validação do contrato OpenAPI antes da integração com o banco.
    """

    # --- Dados mockados para validação do contrato -----------------------
    voluntarios_mock: list[VoluntarioMatch] = [
        VoluntarioMatch(
            nome="Ana Carolina Silva",
            telefone="(11) 98765-4321",
            habilidade_correspondente=necessidade.habilidades_requeridas[0],
            distancia_km=2.3,
        ),
        VoluntarioMatch(
            nome="Carlos Eduardo Santos",
            telefone="(11) 91234-5678",
            habilidade_correspondente=(
                necessidade.habilidades_requeridas[1]
                if len(necessidade.habilidades_requeridas) > 1
                else necessidade.habilidades_requeridas[0]
            ),
            distancia_km=5.7,
        ),
        VoluntarioMatch(
            nome="Mariana Oliveira Costa",
            telefone="(11) 99876-5432",
            habilidade_correspondente=necessidade.habilidades_requeridas[0],
            distancia_km=8.1,
        ),
    ]

    return OrquestracaoResponse(
        total_voluntarios=len(voluntarios_mock),
        voluntarios=voluntarios_mock,
    )
