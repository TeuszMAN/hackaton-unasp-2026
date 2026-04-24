# 🚨 Voluntariado Inteligente para Crises

> **Hackathon IA Descomplicada — UNASP + IBM (2026)**
> _Orquestrando o Voluntariado Inteligente para Situações de Crise_

API de orquestração que conecta **instituições em situação de crise** com **voluntários qualificados**, utilizando correspondência baseada em habilidades (_skill-based volunteering_) e proximidade geográfica. Projetada para integração com o **IBM watsonx Orchestrate** como Skill e com o **watsonx.ai (Granite)** para extração de habilidades a partir de relatos em linguagem natural.

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Arquitetura](#-arquitetura)
- [Stack Tecnológica](#-stack-tecnológica)
- [Pré-requisitos](#-pré-requisitos)
- [Como Rodar](#-como-rodar)
- [Fluxo de Demo Rápido](#-fluxo-de-demo-rápido)
- [Endpoints da API](#-endpoints-da-api)
- [Integração watsonx.ai (para o Vitor)](#-integração-watsonxai-para-o-vitor)
- [Integração watsonx Orchestrate (para o Gabriel)](#-integração-watsonx-orchestrate-para-o-gabriel)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Padrão de Commits](#-padrão-de-commits)
- [Equipe](#-equipe)

---

## 💡 Sobre o Projeto

Em situações de crise — enchentes, deslizamentos, incêndios — cada minuto conta. Este sistema permite que instituições descrevam a emergência **em linguagem natural** (sem preencher formulários) e a API, com ajuda do watsonx.ai, transforma o relato em requisitos técnicos, encontra voluntários compatíveis e facilita o contato, priorizando por proximidade geográfica.

O diferencial: **remover a barreira do formulário no momento mais crítico**. Ninguém preenche campos enquanto a água sobe — o usuário escreve, a IA entende, o sistema age.

### Fluxo principal

```
Instituição → descreve a crise em linguagem natural
            ↓
       watsonx.ai extrai skills + urgência
            ↓
       API executa matchmaking (skill + distância + reputação + disponibilidade)
            ↓
       Orchestrate notifica top-N voluntários em paralelo
            ↓
       Voluntário aceita → contato exposto → atendimento → feedback
            ↓
       Loop agêntico fecha: reputação atualiza para os próximos matches
```

---

## 🏗 Arquitetura

```
┌──────────────────────┐
│  Canais de Entrada   │
│ (Web, WhatsApp, SMS) │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│ watsonx Orchestrate  │  ← Skills (OpenAPI)
│  (maestro + Skills)  │
└──┬────────────────┬──┘
   │                │
┌──▼────────┐   ┌──▼──────────────┐
│  FastAPI  │   │   Notificação   │
│ (músculo) │   │ (WhatsApp/SMS)  │
└──┬────────┘   └─────────────────┘
   │
   ├──► watsonx.ai (Granite)   ← extração de skills + nível de urgência
   │
   ├──► Geocoder (Nominatim)   ← endereço → lat/lng
   │
   └──► PostgreSQL             ← voluntarios, necessidades, vinculos, feedbacks
```

> Documentação técnica detalhada em [`ARCHITECTURE.md`](./ARCHITECTURE.md): modelo de dados completo, algoritmo de matching, estratégia LGPD, roadmap priorizado.

---

## 🛠 Stack Tecnológica

| Camada | Tecnologia | Versão | Papel |
|---|---|---|---|
| Interface/Agente | IBM watsonx Orchestrate | — | Orquestração de fluxos e Skills |
| Cérebro de IA | IBM watsonx.ai (Granite) | — | Extração de habilidades e urgência |
| Backend | Python + FastAPI | 3.11 / 0.111 | Regras de negócio e OpenAPI |
| ORM | SQLAlchemy | 2.0 | Camada de persistência |
| Banco | PostgreSQL | 15 | Armazenamento relacional |
| HTTP async | httpx | 0.27 | Chamadas a geocoder e watsonx.ai |
| Geocoding | OpenStreetMap Nominatim | — | Endereço → coordenadas |
| Infra | Docker + Docker Compose | — | Containerização |
| Ferramenta | pgAdmin 4 | — | Explorador visual do banco |

---

## ✅ Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [Git](https://git-scm.com/)

> Não é necessário instalar Python ou PostgreSQL localmente — tudo roda via Docker.

---

## 🚀 Como Rodar

### 1. Clone o repositório

```bash
git clone https://github.com/TeuszMAN/hackaton-unasp-2026.git
cd hackaton-unasp-2026
```

### 2. (Opcional) Configure o `.env`

```bash
cp .env.example .env
# edite se for plugar o watsonx.ai — caso contrário, o fallback determinístico funciona
```

### 3. Suba os containers

```bash
docker compose up --build
```

### 4. Acesse

| Recurso | URL |
|---|---|
| Health Check | http://localhost:8000/ |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| pgAdmin | http://localhost:5050 |

---

## 🎬 Fluxo de Demo Rápido

Em 4 chamadas você vê o sistema completo funcionando:

**1. Popula o banco com 15 voluntários em São Paulo**

```bash
curl -X POST http://localhost:8000/api/v1/dev/seed-voluntarios-exemplo
```

**2. Registra uma necessidade em linguagem natural**

```bash
curl -X POST http://localhost:8000/api/v1/necessidades \
  -H "Content-Type: application/json" \
  -d '{
    "descricao_crise": "Enchente atingiu nosso abrigo em Vila Nova. Precisamos urgente de atendimento médico para idosos e ajuda para resgate de famílias ilhadas.",
    "endereco": "Vila Nova Conceição, São Paulo - SP",
    "latitude": -23.5889,
    "longitude": -46.6729
  }'
```

Resposta: `202 Accepted` com `resource_id`. Aguarde ~1 segundo para o enriquecimento em background concluir.

**3. Executa matchmaking**

```bash
curl -X POST http://localhost:8000/api/v1/vinculos \
  -H "Content-Type: application/json" \
  -d '{ "necessidade_id": "<RESOURCE_ID>", "top_n": 5 }'
```

Recebe uma lista ranqueada de voluntários com score composto, distância em km e habilidades correspondentes.

**4. Voluntário aceita → contato exposto → conclui → feedback**

```bash
curl -X POST http://localhost:8000/api/v1/vinculos/<VINCULO_ID>/aceitar
curl -X POST http://localhost:8000/api/v1/vinculos/<VINCULO_ID>/concluir
curl -X POST http://localhost:8000/api/v1/vinculos/<VINCULO_ID>/feedback \
  -H "Content-Type: application/json" \
  -d '{ "voluntario_compareceu": true, "skill_adequada": true, "nota": 5 }'
```

O feedback ajusta a reputação do voluntário, que influencia os próximos matches.

---

## 📡 Endpoints da API

### Health

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status da API |

### Voluntários

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/voluntarios` | Cadastra voluntário (202 — extração de skills via watsonx.ai em background) |
| `GET` | `/api/v1/voluntarios` | Lista voluntários com filtros (`disponibilidade`, `habilidade`) |
| `GET` | `/api/v1/voluntarios/{id}` | Consulta um voluntário |
| `PATCH` | `/api/v1/voluntarios/{id}` | Atualiza perfil ou disponibilidade |

### Necessidades

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/necessidades` | Registra demanda de crise (202 — extração em background) |
| `GET` | `/api/v1/necessidades` | Lista necessidades (filtros por `status` e `urgencia`) |
| `GET` | `/api/v1/necessidades/{id}` | Consulta uma necessidade |

### Vínculos (matchmaking)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/vinculos` | Executa matchmaking e cria propostas de vínculo |
| `GET` | `/api/v1/vinculos/{id}` | Consulta um vínculo |
| `POST` | `/api/v1/vinculos/{id}/aceitar` | Voluntário aceita (expõe contato) |
| `POST` | `/api/v1/vinculos/{id}/recusar` | Voluntário recusa |
| `POST` | `/api/v1/vinculos/{id}/concluir` | Registra conclusão do atendimento |
| `POST` | `/api/v1/vinculos/{id}/feedback` | Envia feedback → atualiza reputação |

### Estatísticas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/estatisticas` | Métricas agregadas (totais, tempo médio até aceite, reputação média) |

### Dev / Demo

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/v1/dev/seed-voluntarios-exemplo` | Popula o banco com 15 voluntários em SP |
| `DELETE` | `/api/v1/dev/reset` | Zera todas as tabelas |

> O Swagger UI em `/docs` é o contrato autoritativo — todos os sc