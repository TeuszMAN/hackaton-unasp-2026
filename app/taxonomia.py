"""
Taxonomia controlada de habilidades.

Esta lista é o vocabulário canônico contra o qual o watsonx.ai (Granite)
deve normalizar os relatos livres de voluntários e instituições. Mantê-la
como constante Python no MVP mantém o sistema simples, auditável e fácil
de evoluir — em produção, esta taxonomia viria de uma tabela editável
(`skills_taxonomia`).

Cada entrada contém:
- `codigo`: identificador canônico (ex.: `saude.primeiros_socorros`)
- `label`: rótulo amigável em português
- `categoria`: agrupamento macro
- `sinonimos`: termos que devem ser mapeados para este código. Usado tanto
  pelo fallback determinístico (extração via keywords) quanto como pista
  para o prompt do Granite.
"""

from __future__ import annotations

from typing import TypedDict


class SkillDef(TypedDict):
    codigo: str
    label: str
    categoria: str
    sinonimos: list[str]


SKILLS_TAXONOMIA: list[SkillDef] = [
    # -------------------------------------------------------------- SAÚDE
    {
        "codigo": "saude.primeiros_socorros",
        "label": "Primeiros Socorros",
        "categoria": "saude",
        "sinonimos": ["primeiros socorros", "socorrismo", "first aid", "atendimento emergencial"],
    },
    {
        "codigo": "saude.enfermagem",
        "label": "Enfermagem",
        "categoria": "saude",
        "sinonimos": ["enfermeiro", "enfermeira", "enfermagem", "técnico de enfermagem", "auxiliar de enfermagem"],
    },
    {
        "codigo": "saude.medicina",
        "label": "Medicina",
        "categoria": "saude",
        "sinonimos": ["médico", "médica", "medicina", "doutor", "doutora", "clínico"],
    },
    {
        "codigo": "saude.psicologia",
        "label": "Psicologia",
        "categoria": "saude",
        "sinonimos": ["psicólogo", "psicóloga", "psicologia", "apoio psicológico"],
    },
    {
        "codigo": "saude.fisioterapia",
        "label": "Fisioterapia",
        "categoria": "saude",
        "sinonimos": ["fisioterapeuta", "fisioterapia"],
    },
    # ------------------------------------------------------------ RESGATE
    {
        "codigo": "resgate.aquatico",
        "label": "Resgate Aquático",
        "categoria": "resgate",
        "sinonimos": ["resgate aquático", "salva-vidas", "nadador", "mergulhador", "bote"],
    },
    {
        "codigo": "resgate.altura",
        "label": "Resgate em Altura",
        "categoria": "resgate",
        "sinonimos": ["resgate em altura", "rapel", "alpinismo", "escalada"],
    },
    {
        "codigo": "resgate.bombeiro",
        "label": "Combate a Incêndio",
        "categoria": "resgate",
        "sinonimos": ["bombeiro", "bombeira", "brigadista", "incêndio", "combate a incêndio"],
    },
    {
        "codigo": "resgate.busca",
        "label": "Busca e Salvamento",
        "categoria": "resgate",
        "sinonimos": ["busca e salvamento", "K9", "equipe de busca", "cão de resgate"],
    },
    # ---------------------------------------------------------- LOGÍSTICA
    {
        "codigo": "logistica.transporte",
        "label": "Transporte",
        "categoria": "logistica",
        "sinonimos": ["motorista", "transporte", "caminhão", "van", "carro", "CNH"],
    },
    {
        "codigo": "logistica.distribuicao_alimentos",
        "label": "Distribuição de Alimentos",
        "categoria": "logistica",
        "sinonimos": ["distribuição de alimentos", "cesta básica", "entrega de comida", "doação"],
    },
    {
        "codigo": "logistica.abrigo",
        "label": "Montagem de Abrigo",
        "categoria": "logistica",
        "sinonimos": ["abrigo", "acampamento", "montagem de barraca", "alojamento"],
    },
    {
        "codigo": "logistica.armazenamento",
        "label": "Armazenamento e Triagem",
        "categoria": "logistica",
        "sinonimos": ["armazenamento", "triagem", "organização de doações", "estoque"],
    },
    # -------------------------------------------- CONSTRUÇÃO / ENGENHARIA
    {
        "codigo": "construcao.engenharia_civil",
        "label": "Engenharia Civil",
        "categoria": "construcao",
        "sinonimos": ["engenheiro civil", "engenharia civil", "avaliação estrutural", "estruturas"],
    },
    {
        "codigo": "construcao.eletrica",
        "label": "Instalações Elétricas",
        "categoria": "construcao",
        "sinonimos": ["eletricista", "elétrica", "instalação elétrica"],
    },
    {
        "codigo": "construcao.hidraulica",
        "label": "Instalações Hidráulicas",
        "categoria": "construcao",
        "sinonimos": ["encanador", "hidráulica", "encanamento"],
    },
    # ------------------------------------------------------- COMUNICAÇÃO
    {
        "codigo": "comunicacao.traducao",
        "label": "Tradução e Idiomas",
        "categoria": "comunicacao",
        "sinonimos": ["tradutor", "tradução", "intérprete", "inglês", "espanhol", "libras"],
    },
    {
        "codigo": "comunicacao.radio_amador",
        "label": "Rádio Amador",
        "categoria": "comunicacao",
        "sinonimos": ["radioamador", "rádio amador", "rádio comunicação", "HT"],
    },
    # -------------------------------------------------------- TECNOLOGIA
    {
        "codigo": "tecnologia.suporte_ti",
        "label": "Suporte de TI",
        "categoria": "tecnologia",
        "sinonimos": ["suporte técnico", "TI", "informática", "redes", "computador"],
    },
    # ------------------------------------------------------- PSICOSSOCIAL
    {
        "codigo": "psicossocial.apoio_criancas",
        "label": "Apoio a Crianças",
        "categoria": "psicossocial",
        "sinonimos": ["crianças", "pedagogia", "recreação", "apoio infantil", "brinquedoteca"],
    },
    {
        "codigo": "psicossocial.apoio_idosos",
        "label": "Apoio a Idosos",
        "categoria": "psicossocial",
        "sinonimos": ["idosos", "terceira idade", "cuidador de idoso", "gerontologia"],
    },
    # ------------------------------------------------------- ALIMENTAÇÃO
    {
        "codigo": "alimentacao.cozinha",
        "label": "Cozinha Solidária",
        "categoria": "alimentacao",
        "sinonimos": ["cozinheiro", "cozinheira", "chef", "cozinha", "preparação de refeições"],
    },
    {
        "codigo": "alimentacao.nutricao",
        "label": "Nutrição",
        "categoria": "alimentacao",
        "sinonimos": ["nutricionista", "nutrição", "dieta"],
    },
]


# Índice rápido por código
SKILLS_POR_CODIGO: dict[str, SkillDef] = {s["codigo"]: s for s in SKILLS_TAXONOMIA}


def codigos_validos() -> set[str]:
    """Retorna o conjunto de códigos válidos da taxonomia."""
    return {s["codigo"] for s in SKILLS_TAXONOMIA}


def normalizar_codigos(codigos: list[str]) -> list[str]:
    """Filtra a lista mantendo apenas códigos presentes na taxonomia."""
    validos = codigos_validos()
    return [c for c in codigos if c in validos]
