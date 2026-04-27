"""
Ponto de entrada da API de Voluntariado Inteligente para Crises.

Responsabilidades deste módulo:
  - Instanciar o FastAPI com metadados ricos (usados pelo watsonx Orchestrate
    para interpretar as rotas como Skills).
  - Registrar os routers por domínio.
  - Criar as tabelas no startup (MVP — em produção usar Alembic).
  - Expor o health check.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app import models  # noqa: F401 — necessário para registrar os models no metadata
from app.routers.auth import router as auth_router
from app.routers.dev import router as dev_router
from app.routers.estatisticas import router as estatisticas_router
from app.routers.instituicoes import router as instituicoes_router
from app.routers.necessidades import router as necessidades_router
from app.routers.vinculos import router as vinculos_router
from app.routers.voluntarios import router as voluntarios_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API de Voluntariado Inteligente para Crises",
    description=(
        "API de orquestração que conecta instituições em situação de crise "
        "com voluntários qualificados, utilizando correspondência baseada em "
        "habilidades (skill-based volunteering) e proximidade geográfica. "
        "Projetada para integração com o IBM watsonx Orchestrate como Skill e "
        "com o watsonx.ai (Granite) para extração de habilidades a partir de "
        "relatos livres em linguagem natural."
    ),
    version="0.2.0",
    contact={"name": "Equipe Hackathon UNASP 2026"},
    openapi_tags=[
        {"name": "Health", "description": "Verificação de saúde da API."},
        {"name": "Autenticação", "description": "Login e troca de senha do voluntário."},
        {"name": "Voluntários", "description": "Cadastro e gestão de voluntários."},
        {"name": "Instituições", "description": "Cadastro e gestão de instituições parceiras."},
        {"name": "Necessidades", "description": "Registro de demandas de crise."},
        {"name": "Vínculos", "description": "Matchmaking e ciclo de vida dos vínculos."},
        {"name": "Estatísticas", "description": "Métricas agregadas da plataforma."},
        {"name": "Dev / Demo", "description": "Endpoints auxiliares para demonstração — não usar em produção."},
    ],
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon dev — libera qualquer origem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup — criação de tabelas (MVP)
# ---------------------------------------------------------------------------
@app.on_event("startup")
def criar_tabelas() -> None:
    """Cria as tabelas caso ainda não existam. Em produção, migrar para Alembic."""
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Verifica se a API está online e operacional.",
)
def health_check():
    return {
        "status": "ok",
        "service": "voluntariado-inteligente-api",
        "version": app.version,
    }


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(voluntarios_router)
app.include_router(instituicoes_router)
app.include_router(necessidades_router)
app.include_router(vinculos_router)
app.include_router(estatisticas_router)
app.include_router(dev_router)

# ---------------------------------------------------------------------------
# Frontend estático — deve ser montado por último
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="public", html=True), name="static")
