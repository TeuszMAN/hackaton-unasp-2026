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

# ============================================================================
# DEMO — Instituições
# ============================================================================
INSTITUICOES_DEMO = [
    {
        "nome": "Defesa Civil de São Paulo",
        "cnpj": "12345678000101",
        "regiao": "São Paulo - SP",
        "verificada": True,
        "contato": {
            "telefone": "(11) 4000-1000",
            "email": "contato@defesacivilsp.org",
            "cidade": "São Paulo - SP",
            "responsavel": "Marcos Almeida",
        },
    },
    {
        "nome": "Instituto Esperança Viva",
        "cnpj": "22345678000102",
        "regiao": "Guarulhos - SP",
        "verificada": True,
        "contato": {
            "telefone": "(11) 4000-2000",
            "email": "apoio@esperancaviva.org",
            "cidade": "Guarulhos - SP",
            "responsavel": "Fernanda Lima",
        },
    },
    {
        "nome": "ONG Mãos Unidas",
        "cnpj": "32345678000103",
        "regiao": "Osasco - SP",
        "verificada": False,
        "contato": {
            "telefone": "(11) 4000-3000",
            "email": "contato@maosunidas.org",
            "cidade": "Osasco - SP",
            "responsavel": "Carlos Eduardo",
        },
    },
]

# ============================================================================
# DEMO — Crises / Necessidades
# ============================================================================
CRISES_DEMO = [
    {
        "descricao_crise": (
            "Alagamento severo após chuva intensa deixando dezenas "
            "de famílias desalojadas e sem acesso a alimentos."
        ),
        "endereco_texto": "Marginal Tietê, São Paulo - SP",
        "nivel_urgencia": "critica",
        "status": "aberta",
        "habilidades_requeridas": [
            "resgate.aquatico",
            "saude.primeiros_socorros",
            "logistica.abrigo",
        ],
    },
    {
        "descricao_crise": (
            "Incêndio em comunidade com necessidade urgente de "
            "apoio médico e distribuição de alimentos."
        ),
        "endereco_texto": "Heliópolis, São Paulo - SP",
        "nivel_urgencia": "alta",
        "status": "em_atendimento",
        "habilidades_requeridas": [
            "resgate.bombeiro",
            "alimentacao.cozinha",
            "saude.enfermagem",
        ],
    },
    {
        "descricao_crise": (
            "Queda de energia em hospital comunitário exigindo "
            "manutenção elétrica emergencial."
        ),
        "endereco_texto": "Santo André - SP",
        "nivel_urgencia": "alta",
        "status": "aberta",
        "habilidades_requeridas": [
            "construcao.eletrica",
            "tecnologia.suporte_ti",
        ],
    },
    {
        "descricao_crise": (
            "Abrigo temporário superlotado precisando de suporte "
            "psicológico para crianças e idosos."
        ),
        "endereco_texto": "Guarulhos - SP",
        "nivel_urgencia": "media",
        "status": "aberta",
        "habilidades_requeridas": [
            "saude.psicologia",
            "psicossocial.apoio_criancas",
            "psicossocial.apoio_idosos",
        ],
    },
]

# ============================================================================
# ROUTE — Seed Instituições + Crises
# ============================================================================
@router.post(
    "/seed-demo-extra",
    summary="[DEV] Seed de instituições e crises",
)
def seed_demo_extra(db: Session = Depends(get_db)):

    instituicoes_criadas = 0
    crises_criadas = 0

    instituicoes_ids = []

    # ----------------------------------------------------------------------
    # Instituições
    # ----------------------------------------------------------------------
    for item in INSTITUICOES_DEMO:

        existe = (
            db.query(models.Instituicao)
            .filter(models.Instituicao.nome == item["nome"])
            .first()
        )

        if existe:
            instituicoes_ids.append(existe.id)
            continue

        nova = models.Instituicao(
            nome=item["nome"],
            cnpj=item["cnpj"],
            regiao=item["regiao"],
            verificada=item["verificada"],
            contato=item["contato"],
        )

        db.add(nova)
        db.flush()

        instituicoes_ids.append(nova.id)
        instituicoes_criadas += 1

    # ----------------------------------------------------------------------
    # Crises
    # ----------------------------------------------------------------------
    for idx, item in enumerate(CRISES_DEMO):

        existe = (
            db.query(models.Necessidade)
            .filter(
                models.Necessidade.descricao_crise
                == item["descricao_crise"]
            )
            .first()
        )

        if existe:
            continue

        necessidade = models.Necessidade(
            descricao_crise=item["descricao_crise"],
            endereco_texto=item["endereco_texto"],
            nivel_urgencia=item["nivel_urgencia"],
            status=item["status"],
            habilidades_requeridas=item["habilidades_requeridas"],
            instituicao_id=instituicoes_ids[
                idx % len(instituicoes_ids)
            ] if instituicoes_ids else None,
        )

        db.add(necessidade)
        crises_criadas += 1

    db.commit()

    return {
        "ok": True,
        "instituicoes_criadas": instituicoes_criadas,
        "crises_criadas": crises_criadas,
    }



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
