"""
Schemas Pydantic (validação e OpenAPI).

Schemas com descrições e exemplos ricos — é o contrato que o watsonx
Orchestrate irá ler para interpretar a API como Skill.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    NivelUrgencia,
    StatusNecessidade,
    StatusVinculo,
    StatusVoluntario,
)


# ===========================================================================
# Voluntários
# ===========================================================================
class VoluntarioCreate(BaseModel):
    """
    Cadastro de voluntário a partir de relato livre em linguagem natural.

    O texto em `relato` é enviado ao watsonx.ai (Granite) para extração
    de habilidades normalizadas contra a taxonomia controlada.
    """

    nome: str = Field(..., min_length=2, max_length=200, json_schema_extra={"example": "Ana Carolina Silva"})
    telefone: str = Field(..., min_length=8, max_length=40, json_schema_extra={"example": "(11) 98765-4321"})
    email: EmailStr | None = Field(None, json_schema_extra={"example": "ana.silva@email.com"})

    instituicao_id: uuid.UUID | None = Field(
        None,
        description="ID da instituição à qual o voluntário está vinculado (opcional).",
    )

    relato: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description=(
            "Relato livre do voluntário descrevendo suas competências, "
            "experiências e disponibilidade. Pode incluir profissão, cursos, "
            "horários disponíveis e restrições."
        ),
        json_schema_extra={
            "example": (
                "Sou enfermeira há 10 anos, moro na zona sul de São Paulo. "
                "Tenho experiência com primeiros socorros e atendimento "
                "emergencial. Disponível nos fins de semana."
            )
        },
    )

    endereco: str | None = Field(
        None,
        max_length=300,
        description="Endereço textual do voluntário para geocodificação.",
        json_schema_extra={"example": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP"},
    )
    latitude: float | None = Field(None, ge=-90, le=90, json_schema_extra={"example": -23.5617})
    longitude: float | None = Field(None, ge=-180, le=180, json_schema_extra={"example": -46.6559})

    consentimento_lgpd: bool = Field(
        ...,
        description="Consentimento explícito para o tratamento de dados pessoais conforme a LGPD.",
        json_schema_extra={"example": True},
    )


class VoluntarioUpdate(BaseModel):
    """Atualização parcial de perfil do voluntário."""

    disponibilidade: StatusVoluntario | None = None
    telefone: str | None = Field(None, min_length=8, max_length=40)
    email: EmailStr | None = None
    habilidades: list[str] | None = Field(
        None, description="Lista de códigos da taxonomia (ex.: 'saude.primeiros_socorros')."
    )


class VoluntarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    telefone: str
    email: str | None
    habilidades: list[str]
    endereco_texto: str | None
    latitude: float | None
    longitude: float | None
    disponibilidade: StatusVoluntario
    reputacao: float
    criado_em: datetime


class VoluntarioPublico(BaseModel):
    """Versão reduzida exposta antes do aceite de vínculo (LGPD)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str = Field(..., description="Nome completo do voluntário.")
    iniciais: str = Field(..., description="Apenas iniciais do nome (ex.: 'A. C. S.').")
    habilidades: list[str]
    reputacao: float


class VoluntarioVerificacao(BaseModel):
    """Resultado da verificação de duplicidade de cadastro de voluntário."""

    existe: bool = Field(..., description="Indica se já existe voluntário com algum dos identificadores informados.")
    campos_duplicados: list[str] = Field(
        default_factory=list,
        description="Campos que coincidem com o cadastro existente (ex.: ['telefone', 'email']).",
    )
    voluntario_id: uuid.UUID | None = Field(
        None,
        description="ID interno do voluntário existente, quando `existe=True`. Não expõe dados pessoais.",
    )


# ===========================================================================
# Necessidades
# ===========================================================================
class NecessidadeCreate(BaseModel):
    """
    Registro de uma necessidade emergencial a partir de relato livre da
    instituição ou coordenador.
    """

    descricao_crise: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description=(
            "Descrição em linguagem natural da situação de crise, "
            "necessidades percebidas e contexto."
        ),
        json_schema_extra={
            "example": (
                "Enchente atingiu nosso abrigo comunitário no bairro Vila Nova. "
                "Precisamos urgente de atendimento médico para idosos e ajuda "
                "para resgate de famílias ilhadas."
            )
        },
    )
    endereco: str | None = Field(
        None,
        max_length=300,
        json_schema_extra={"example": "Rua das Flores, 123 - Vila Nova, São Paulo - SP"},
    )
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    nivel_urgencia: NivelUrgencia | None = Field(
        None,
        description=(
            "Nível de urgência. Se omitido, será inferido pelo watsonx.ai "
            "a partir da descrição."
        ),
        json_schema_extra={"example": "critico"},
    )

    instituicao_id: uuid.UUID | None = None


class NecessidadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instituicao_id: uuid.UUID | None
    descricao_crise: str
    habilidades_requeridas: list[str]
    endereco_texto: str | None
    latitude: float | None
    longitude: float | None
    nivel_urgencia: NivelUrgencia
    status: StatusNecessidade
    criado_em: datetime


# ===========================================================================
# Vínculos (matches)
# ===========================================================================
class VinculoCreate(BaseModel):
    """Solicitação de matchmaking para uma necessidade já registrada."""

    necessidade_id: uuid.UUID = Field(
        ...,
        description="ID da necessidade para a qual se deseja encontrar voluntários.",
    )
    top_n: int = Field(
        5, ge=1, le=20, description="Quantidade máxima de voluntários a recomendar."
    )


class MatchRecomendado(BaseModel):
    """Recomendação individual retornada pelo matchmaking."""

    model_config = ConfigDict(from_attributes=True)

    vinculo_id: uuid.UUID
    voluntario: VoluntarioPublico
    score_match: float = Field(..., description="Score composto entre 0 e 1.")
    habilidades_correspondentes: list[str]
    distancia_km: float | None
    distancia_m: int | None = Field(
        None, description="Distância em metros (arredondada). `null` quando não há coordenadas."
    )
    recomendado: bool = Field(
        False,
        description="`True` para o voluntário marcado como recomendação primária (menor distância).",
    )
    status: StatusVinculo
    justificativa: str | None = Field(
        None,
        description="Frase curta gerada pela IA explicando por que o voluntário foi recomendado.",
    )


class MatchmakingResponse(BaseModel):
    necessidade_id: uuid.UUID
    nivel_urgencia: NivelUrgencia
    total_recomendados: int
    recomendacoes: list[MatchRecomendado]


class NecessidadeResumo(BaseModel):
    """Resumo de necessidade exibido na caixa de aprovação."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    descricao_crise: str
    endereco_texto: str | None
    nivel_urgencia: NivelUrgencia
    criado_em: datetime


class GrupoAprovacao(BaseModel):
    """Conjunto de candidatos aguardando aprovação para uma mesma necessidade."""

    necessidade: NecessidadeResumo
    candidatos: list[MatchRecomendado]


class VinculoOut(BaseModel):
    """Visão completa de um vínculo — expõe contato após aceite."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    necessidade_id: uuid.UUID
    voluntario_id: uuid.UUID
    status: StatusVinculo
    score_match: float
    habilidades_correspondentes: list[str]
    distancia_km: float | None
    proposto_em: datetime
    aceito_em: datetime | None
    concluido_em: datetime | None


# ===========================================================================
# Feedback
# ===========================================================================
class FeedbackCreate(BaseModel):
    voluntario_compareceu: bool = Field(..., json_schema_extra={"example": True})
    skill_adequada: bool = Field(..., json_schema_extra={"example": True})
    nota: int = Field(..., ge=1, le=5, json_schema_extra={"example": 5})
    comentario: str | None = Field(None, max_length=1000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vinculo_id: uuid.UUID
    voluntario_compareceu: bool
    skill_adequada: bool
    nota: int
    comentario: str | None
    criado_em: datetime


# ===========================================================================
# Estatísticas
# ===========================================================================
class EstatisticasOut(BaseModel):
    total_voluntarios: int
    voluntarios_disponiveis: int
    total_necessidades: int
    necessidades_abertas: int
    necessidades_criticas_abertas: int
    total_vinculos: int
    vinculos_aceitos: int
    vinculos_concluidos: int
    tempo_medio_ate_aceite_minutos: float | None
    reputacao_media: float | None


# ===========================================================================
# Instituições
# ===========================================================================
class InstituicaoCreate(BaseModel):
    """Cadastro de uma instituição parceira."""

    nome: str = Field(..., min_length=2, max_length=200, json_schema_extra={"example": "Abrigo Esperança"})
    cnpj: str | None = Field(
        None,
        max_length=20,
        description="CNPJ da instituição (opcional). Formato: XX.XXX.XXX/XXXX-XX.",
        json_schema_extra={"example": "12.345.678/0001-90"},
    )
    regiao: str | None = Field(
        None,
        max_length=120,
        description="Região atendida (ex.: 'Zona Sul - SP', 'Norte - Manaus').",
        json_schema_extra={"example": "Zona Sul - SP"},
    )
    contato: dict | None = Field(
        None,
        description="Dados de contato em formato livre (email, telefone, responsável, etc.).",
        json_schema_extra={"example": {"email": "contato@abrigo.org", "telefone": "(11) 3456-7890", "responsavel": "Maria Lima"}},
    )


class InstituicaoUpdate(BaseModel):
    """Atualização parcial de uma instituição."""

    nome: str | None = Field(None, min_length=2, max_length=200)
    cnpj: str | None = Field(None, max_length=20)
    regiao: str | None = Field(None, max_length=120)
    verificada: bool | None = None
    contato: dict | None = None


class InstituicaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cnpj: str | None
    regiao: str | None
    verificada: bool
    contato: dict | None
    criado_em: datetime


class InstituicaoVerificacao(BaseModel):
    """Resultado da verificação de duplicidade de cadastro de instituição."""

    existe: bool = Field(..., description="Indica se já existe instituição com o CNPJ informado.")
    instituicao_id: uuid.UUID | None = Field(
        None,
        description="ID interno da instituição existente, quando `existe=True`. Não expõe dados de contato.",
    )


# ===========================================================================
# Autenticação de voluntário
# ===========================================================================
class VoluntarioCadastroAceito(BaseModel):
    """
    Resposta do cadastro de voluntário.

    Carrega a senha temporária em texto claro — entregar somente ao próprio
    voluntário (no chat do agente) e nunca persistir no log.
    """

    task_id: uuid.UUID
    voluntario_id: uuid.UUID
    login_id: str = Field(
        ...,
        description="Identificador para login (primeiros 8 caracteres do voluntario_id).",
    )
    senha_temporaria: str = Field(
        ..., description="Senha temporária em texto claro. Válida por tempo limitado."
    )
    senha_temp_expira_em: datetime
    mensagem: str


class LoginRequest(BaseModel):
    login_id: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Primeiros 8 caracteres do voluntario_id.",
    )
    senha: str = Field(..., min_length=4, max_length=200)


class LoginResponse(BaseModel):
    token: str
    voluntario_id: uuid.UUID
    nome: str
    precisa_trocar_senha: bool
    expira_em: datetime


class TrocarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=4, max_length=200)
    nova_senha: str = Field(..., min_length=6, max_length=200)


class RegiaoOut(BaseModel):
    regiao: str
    total_instituicoes: int


# ===========================================================================
# Assíncrono — retorno padrão para processamento em background
# ===========================================================================
class TaskAceita(BaseModel):
    """Resposta 202 Accepted padrão."""

    task_id: uuid.UUID
    resource_id: uuid.UUID
    mensagem: str = Field(
        ...,
        json_schema_extra={"example": "Cadastro recebido — enriquecimento em andamento."},
    )
