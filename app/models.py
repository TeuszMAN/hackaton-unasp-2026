"""
Models ORM (SQLAlchemy 2.0).

Este módulo concentra todas as entidades persistidas no PostgreSQL.
Em um projeto maior estariam divididas em vários arquivos, mas para o
escopo do hackathon centralizar reduz atrito.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class NivelUrgencia(str, enum.Enum):
    baixo = "baixo"
    medio = "medio"
    alto = "alto"
    critico = "critico"


class StatusNecessidade(str, enum.Enum):
    aberta = "aberta"
    em_atendimento = "em_atendimento"
    resolvida = "resolvida"
    cancelada = "cancelada"


class StatusVoluntario(str, enum.Enum):
    disponivel = "disponivel"
    ocupado = "ocupado"
    em_missao = "em_missao"
    inativo = "inativo"


class StatusVinculo(str, enum.Enum):
    proposto = "proposto"
    aceito = "aceito"
    recusado = "recusado"
    em_atendimento = "em_atendimento"
    concluido = "concluido"
    cancelado = "cancelado"


# ---------------------------------------------------------------------------
# Voluntário
# ---------------------------------------------------------------------------
class Voluntario(Base):
    __tablename__ = "voluntarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    telefone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    relato_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    habilidades: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    endereco_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    disponibilidade: Mapped[StatusVoluntario] = mapped_column(
        SAEnum(StatusVoluntario, name="status_voluntario"),
        default=StatusVoluntario.disponivel,
        nullable=False,
    )
    ultima_missao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reputacao: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)

    consentimento_lgpd: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    vinculos: Mapped[list["Vinculo"]] = relationship(
        back_populates="voluntario", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Instituição
# ---------------------------------------------------------------------------
class Instituicao(Base):
    __tablename__ = "instituicoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    verificada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contato: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    necessidades: Mapped[list["Necessidade"]] = relationship(
        back_populates="instituicao", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Necessidade de Crise
# ---------------------------------------------------------------------------
class Necessidade(Base):
    __tablename__ = "necessidades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instituicao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instituicoes.id"), nullable=True
    )

    descricao_crise: Mapped[str] = mapped_column(Text, nullable=False)
    habilidades_requeridas: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )

    endereco_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    nivel_urgencia: Mapped[NivelUrgencia] = mapped_column(
        SAEnum(NivelUrgencia, name="nivel_urgencia"),
        default=NivelUrgencia.alto,
        nullable=False,
    )
    status: Mapped[StatusNecessidade] = mapped_column(
        SAEnum(StatusNecessidade, name="status_necessidade"),
        default=StatusNecessidade.aberta,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    instituicao: Mapped[Instituicao | None] = relationship(back_populates="necessidades")
    vinculos: Mapped[list["Vinculo"]] = relationship(
        back_populates="necessidade", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Vínculo (match voluntário ↔ necessidade)
# ---------------------------------------------------------------------------
class Vinculo(Base):
    __tablename__ = "vinculos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    necessidade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("necessidades.id"), nullable=False
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id"), nullable=False
    )

    status: Mapped[StatusVinculo] = mapped_column(
        SAEnum(StatusVinculo, name="status_vinculo"),
        default=StatusVinculo.proposto,
        nullable=False,
    )
    score_match: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    habilidades_correspondentes: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    distancia_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    proposto_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    aceito_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    necessidade: Mapped[Necessidade] = relationship(back_populates="vinculos")
    voluntario: Mapped[Voluntario] = relationship(back_populates="vinculos")
    feedback: Mapped["Feedback | None"] = relationship(
        back_populates="vinculo", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Feedback pós-atendimento
# ---------------------------------------------------------------------------
class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vinculo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vinculos.id"), nullable=False, unique=True
    )

    voluntario_compareceu: Mapped[bool] = mapped_column(Boolean, nullable=False)
    skill_adequada: Mapped[bool] = mapped_column(Boolean, nullable=False)
    nota: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    vinculo: Mapped[Vinculo] = relationship(back_populates="feedback")
