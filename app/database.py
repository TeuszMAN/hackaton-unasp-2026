"""
Configuração do SQLAlchemy.

Expõe o `engine`, a fábrica `SessionLocal`, a `Base` declarativa e a
dependência `get_db` a ser usada nos routers do FastAPI.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon123@db:5432/voluntariado_db",
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


class Base(DeclarativeBase):
    """Base declarativa comum a todos os models ORM."""


def get_db():
    """Dependência FastAPI: fornece uma sessão e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
