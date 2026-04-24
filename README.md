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

> O Swagger UI em `/docs` é o contrato autoritativo — todos os schemas, exemplos e descrições estão lá e são consumidos pelo watsonx Orchestrate.

---

## 🧠 Integração watsonx.ai (para o Vitor)

A fronteira entre backend e IA está em `app/services/ai.py`. A interface `IAExtracaoService` define dois métodos a implementar:

```python
class IAExtracaoService:
    async def extrair_habilidades_voluntario(self, relato: str) -> ExtracaoVoluntario: ...
    async def extrair_requisitos_necessidade(self, descricao: str) -> ExtracaoNecessidade: ...
```

Há duas implementações:

- `IAFallbackKeywords` — fallback determinístico baseado em match contra os sinônimos da `SKILLS_TAXONOMIA`. Usado como default e também se o watsonx.ai estiver indisponível. Permite rodar a demo sem credenciais IBM.
- `IAWatsonxService` — esqueleto para a integração real. Já traz prompts sugeridos em docstring, leitura das env vars e delega para o fallback enquanto o `TODO(Vitor)` não for implementado.

**Para ativar o watsonx.ai:**

```bash
# .env
IA_PROVIDER=watsonx
WATSONX_API_KEY=...
WATSONX_PROJECT_ID=...
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

A factory `get_ia_service()` faz a seleção. O restante do código não precisa mudar.

---

## 🎛 Integração watsonx Orchestrate (para o Gabriel)

A API expõe um contrato OpenAPI rico em `http://localhost:8000/openapi.json` pronto para ser importado como Skill no watsonx Orchestrate. Descrições semânticas, exemplos explícitos em cada campo e tags temáticas (`Voluntários`, `Necessidades`, `Vínculos`, `Estatísticas`) facilitam a interpretação automática.

As rotas recomendadas para virar Skills:

- **"Cadastrar voluntário"** → `POST /api/v1/voluntarios`
- **"Registrar necessidade de crise"** → `POST /api/v1/necessidades`
- **"Encontrar voluntários para uma crise"** → `POST /api/v1/vinculos`
- **"Voluntário aceita missão"** → `POST /api/v1/vinculos/{id}/aceitar`
- **"Concluir atendimento"** → `POST /api/v1/vinculos/{id}/concluir`
- **"Enviar feedback pós-atendimento"** → `POST /api/v1/vinculos/{id}/feedback`

---

## ⚙️ Variáveis de Ambiente

Veja `.env.example` para a lista completa. Resumo:

| Variável | Obrigatória | Default | Função |
|---|---|---|---|
| `DATABASE_URL` | não | `postgresql://hackathon:hackathon123@db:5432/voluntariado_db` | Conexão com o Postgres |
| `IA_PROVIDER` | não | `fallback` | `fallback` ou `watsonx` |
| `WATSONX_API_KEY` | se `IA_PROVIDER=watsonx` | — | Chave do watsonx.ai |
| `WATSONX_PROJECT_ID` | se `IA_PROVIDER=watsonx` | — | Project ID do watsonx.ai |
| `WATSONX_MODEL_ID` | não | `ibm/granite-3-8b-instruct` | Modelo Granite |
| `WATSONX_URL` | não | `https://us-south.ml.cloud.ibm.com` | Endpoint regional |

---

## 📁 Estrutura do Projeto

```
hackaton-unasp-2026/
├── main.py                     # Ponto de entrada FastAPI (wire up)
├── app/
│   ├── database.py             # Engine SQLAlchemy + get_db
│   ├── models.py               # Models ORM (Voluntario, Necessidade, Vinculo, ...)
│   ├── schemas.py              # Schemas Pydantic (I/O + OpenAPI)
│   ├── taxonomia.py            # Vocabulário controlado de habilidades (24 skills)
│   ├── services/
│   │   ├── ai.py               # Interface p/ watsonx.ai + fallback determinístico
│   │   ├── geocoding.py        # Geocoder Nominatim (async)
│   │   └── matching.py         # Haversine + score ponderado por urgência
│   └── routers/
│       ├── voluntarios.py      # CRUD + cadastro assíncrono
│       ├── necessidades.py     # CRUD + cadastro assíncrono
│       ├── vinculos.py         # Matchmaking + ciclo de vida + feedback
│       ├── estatisticas.py     # Métricas agregadas
│       └── dev.py              # Seed de demo e reset
├── ARCHITECTURE.md             # Documento técnico detalhado
├── requirements.txt
├── Dockerfile
├── docker-compose.yml          # API + Postgres + pgAdmin
├── pgadmin-servers.json        # Conexão pré-configurada do pgAdmin
├── .env.example
├── .gitignore
└── README.md
```

---

## 📝 Padrão de Commits

Trabalhamos com **[Conventional Commits](https://www.conventionalcommits.org/)**:

| Prefixo | Uso |
|---|---|
| `feat:` | Novas funcionalidades |
| `fix:` | Correções de bugs |
| `chore:` | Infra / dependências / configuração |
| `docs:` | Documentação |
| `refactor:` | Refatoração sem mudar comportamento |
| `test:` | Adição ou correção de testes |

**Exemplo:**

```
feat: adiciona algoritmo de matchmaking com score ponderado por urgência
```

---

## 👥 Equipe

- Gabriel Yoshino
- Lais Gonçalves
- Mateus Alves
- Vitor Bueno
