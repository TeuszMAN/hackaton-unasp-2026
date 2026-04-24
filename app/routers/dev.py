"""
Router — Endpoints de desenvolvimento / demo.

NÃO expor em produção. Fornecem dados de exemplo para que o Gabriel
(Orchestrate) e o Vitor (watsonx.ai) consigam validar o fluxo
imediatamente, sem precisar cadastrar manualmente dezenas de voluntários.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db


router = APIRouter(prefix="/api/v1/dev", tags=["Dev / Demo"])


# Voluntários espalhados pela região metropolitana de São Paulo.
# Lat/Lng aproximadas (não é um mapa exato, é só para demo).
VOLUNTARIOS_DEMO = [
    {
        "nome": "Ana Carolina Silva", "telefone": "(11) 98765-4321",
        "habilidades": ["saude.enfermagem", "saude.primeiros_socorros"],
        "endereco": "Vila Nova Conceição, São Paulo - SP",
        "latitude": -23.5889, "longitude": -46.6729, "reputacao": 4.7,
    },
    {
        "nome": "Carlos Eduardo Santos", "telefone": "(11) 91234-5678",
        "habilidades": ["resgate.aquatico", "saude.primeiros_socorros"],
        "endereco": "Santo Amaro, São Paulo - SP",
        "latitude": -23.6540, "longitude": -46.7075, "reputacao": 4.5,
    },
    {
        "nome": "Mariana Oliveira Costa", "telefone": "(11) 99876-5432",
        "habilidades": ["logistica.transporte", "alimentacao.cozinha"],
        "endereco": "Sé, São Paulo - SP",
        "latitude": -23.5506, "longitude": -46.6333, "reputacao": 4.2,
    },
    {
        "nome": "João Pedro Almeida", "telefone": "(11) 98111-2222",
        "habilidades": ["construcao.engenharia_civil", "construcao.eletrica"],
        "endereco": "Itaquera, São Paulo - SP",
        "latitude": -23.5408, "longitude": -46.4601, "reputacao": 4.0,
    },
    {
        "nome": "Fernanda Ribeiro", "telefone": "(11) 98222-3333",
        "habilidades": ["saude.medicina", "saude.primeiros_socorros"],
        "endereco": "Pinheiros, São Paulo - SP",
        "latitude": -23.5680, "longitude": -46.7015, "reputacao": 4.9,
    },
    {
        "nome": "Pedro Henrique Souza", "telefone": "(11) 98333-4444",
        "habilidades": ["resgate.bombeiro", "resgate.busca"],
        "endereco": "Santana, São Paulo - SP",
        "latitude": -23.5018, "longitude": -46.6269, "reputacao": 4.6,
    },
    {
        "nome": "Beatriz Castro", "telefone": "(11) 98444-5555",
        "habilidades": ["psicossocial.apoio_criancas", "saude.psicologia"],
        "endereco": "Ipiranga, São Paulo - SP",
        "latitude": -23.5905, "longitude": -46.6121, "reputacao": 4.8,
    },
    {
        "nome": "Rodrigo Mendes", "telefone": "(11) 98555-6666",
        "habilidades": ["tecnologia.suporte_ti", "comunicacao.radio_amador"],
        "endereco": "Consolação, São Paulo - SP",
        "latitude": -23.5550, "longitude": -46.6596, "reputacao": 4.3,
    },
    {
        "nome": "Lucas Ferreira", "telefone": "(11) 98666-7777",
        "habilidades": ["logistica.distribuicao_alimentos", "logistica.abrigo"],
        "endereco": "Santo André - SP",
        "latitude": -23.6633, "longitude": -46.5383, "reputacao": 4.4,
    },
    {
        "nome": "Patricia Gomes", "telefone": "(11) 98777-8888",
        "habilidades": ["saude.fisioterapia"],
        "endereco": "Tatuapé, São Paulo - SP",
        "latitude": -23.5402, "longitude": -46.5767, "reputacao": 4.1,
    },
    {
        "nome": "Gabriel Martins", "telefone": "(11) 98888-9999",
        "habilidades": ["resgate.altura", "construcao.hidraulica"],
        "endereco": "Santo André - SP",
        "latitude": -23.6629, "longitude": -46.5283, "reputacao": 4.5,
    },
    {
        "nome": "Isabella Rocha", "telefone": "(11) 98999-1111",
        "habilidades": ["psicossocial.apoio_idosos", "saude.enfermagem"],
        "endereco": "Guarulhos - SP",
        "latitude": -23.4628, "longitude": -46.5333, "reputacao": 4.6,
    },
    {
        "nome": "Rafael Lima", "telefone": "(11) 97111-2222",
        "habilidades": ["comunicacao.traducao", "tecnologia.suporte_ti"],
        "endereco": "Osasco - SP",
        "latitude": -23.5329, "longitude": -46.7916, "reputacao": 4.2,
    },
    {
        "nome": "Camila Barbosa", "telefone": "(11) 97222-3333",
        "habilidades": ["alimentacao.nutricao", "alimentacao.cozinha"],
        "endereco": "Diadema - SP",
        "latitude": -23.6859, "longitude": -46.6205, "reputacao": 4.4,
    },
    {
        "nome": "Thiago Pereira", "telefone": "(11) 97333-4444",
        "habilidades": ["saude.psicologia", "psicossocial.apoio_criancas"],
        "endereco": "São Caetano do Sul - SP",
        "latitude": -23.6229, "longitude": -46.5547, "reputacao": 4.7,
    },
]


@router.post(
    "/seed-voluntarios-exemplo",
    summary="[DEV] Carrega voluntários de demonstração",
    description=(
        "Popula o banco com ~15 voluntários distribuídos na RMSP. "
        "Operação idempotente: só insere se o nome ainda não existir."
    ),
)
def seed_voluntarios(db: Session = Depends(get_db)):
    criados = 0
    for v in VOLUNTARIOS_DEMO:
        existe = (
            db.query(models.Voluntario)
            .filter(models.Voluntario.nome == v["nome"])
            .first()
        )
        if existe:
            continue
        voluntario = models.Voluntario(
            nome=v["nome"],
            telefone=v["telefone"],
            habilidades=v["habilidades"],
            endereco_texto=v["endereco"],
            latitude=v["latitude"],
            longitude=v["longitude"],
            disponibilidade=models.StatusVoluntario.disponivel,
            reputacao=v["reputacao"],
            consentimento_lgpd=True,
            relato_original="(dados de demo)",
        )
        db.add(voluntario)
        criados += 1
    db.commit()
    return {
        "voluntarios_criados": criados,
        "total_na_base": db.query(models.Voluntario).count(),
    }


@router.delete(
    "/reset",
    summary="[DEV] Zera todas as tabelas",
    description="Remove todos os voluntários, necessidades, vínculos e feedbacks. Uso estritamente de desenvolvimento.",
)
def reset_tudo(db: Session = Depends(get_db)):
    db.query(models.Feedback).delete()
    db.query(models.Vinculo).delete()
    db.query(models.Necessidade).delete()
    db.query(models.Voluntario).delete()
    db.query(models.Instituicao).delete()
    db.commit()
    return {"ok": True}
