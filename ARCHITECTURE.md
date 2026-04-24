# Arquitetura — Voluntariado Inteligente para Crises

> **Hackathon IA Descomplicada (UNASP + IBM) — 2026**
> Documento técnico formal da arquitetura da solução, consolidando a proposta inicial, análise crítica e plano de evolução.

---

## Sumário

- [1. Visão Geral](#1-visão-geral)
- [2. Princípios de Design](#2-princípios-de-design)
- [3. Fluxo Agêntico (The Agentic Loop)](#3-fluxo-agêntico-the-agentic-loop)
- [4. Stack Tecnológica](#4-stack-tecnológica)
- [5. Modelo de Dados](#5-modelo-de-dados)
- [6. Contratos da API (OpenAPI)](#6-contratos-da-api-openapi)
- [7. Algoritmo de Matchmaking](#7-algoritmo-de-matchmaking)
- [8. Diagrama Lógico](#8-diagrama-lógico)
- [9. Resiliência, Segurança e LGPD](#9-resiliência-segurança-e-lgpd)
- [10. Observabilidade](#10-observabilidade)
- [11. Roadmap Priorizado para o Hackathon](#11-roadmap-priorizado-para-o-hackathon)
- [12. Narrativa para o Pitch](#12-narrativa-para-o-pitch)

---

## 1. Visão Geral

A solução é uma **API de orquestração** que conecta instituições em situação de crise (enchentes, deslizamentos, incêndios, desabrigos) a voluntários qualificados, utilizando correspondência baseada em habilidades (*skill-based volunteering*) e proximidade geográfica.

O núcleo de coordenação é o **IBM watsonx Orchestrate**, que interpreta a API como um conjunto de **Skills** e executa o fluxo de negócio de ponta a ponta. A inteligência de linguagem é delegada ao **watsonx.ai (modelos Granite)**, que transforma relatos livres — tanto do voluntário quanto da instituição — em dados estruturados acionáveis.

O diferencial central: **remover a barreira do formulário em um momento de crise**. Ninguém preenche campos estruturados enquanto a água sobe. O usuário descreve a situação em linguagem natural; a solução faz o resto.

---

## 2. Princípios de Design

- **Orchestrate é maestro, FastAPI é músculo.** Toda a inteligência de linguagem é concentrada no watsonx.ai via Orchestrate. A API é determinística, testável e auditável.
- **Simetria voluntário ↔ instituição.** Ambos os lados produzem o mesmo tipo de objeto canônico (perfil de capacidade vs. perfil de demanda), reduzindo o matching a um problema de similaridade bem definido.
- **Contrato OpenAPI como cidadão de primeira classe.** Descrições ricas, exemplos explícitos e versionamento (`/api/v1/`) são pré-requisito para o Orchestrate interpretar as rotas como Skills.
- **Loop fechado de aprendizado.** Sem feedback pós-atendimento, a solução é apenas um recomendador ingênuo. O `feedback` realimenta a reputação e o ranking futuro.
- **Privacidade por padrão (LGPD).** Dados de contato só são expostos após o match ser aceito pelo voluntário.
- **Resiliência em crise.** O pior cenário é a rota travar esperando o LLM. Fallback determinístico é obrigatório.

---

## 3. Fluxo Agêntico (The Agentic Loop)

### 3.1 Fluxo de Entrada — Voluntário

1. O voluntário envia um **relato livre** sobre suas competências, experiência e disponibilidade (ex.: *"Sou enfermeira há 10 anos, moro na zona sul e tenho fins de semana livres"*).
2. O **Orchestrate** aciona `POST /api/v1/voluntarios`.
3. A API envia o relato ao **watsonx.ai (Granite)** para:
   - Extração de habilidades normalizadas contra uma **taxonomia controlada** (ex.: `saude.enfermagem`, `resgate.aquatico`, `logistica.transporte`).
   - Inferência de disponibilidade e experiência.
4. O endereço é **geocodificado** em `latitude`/`longitude`.
5. O perfil estruturado é persistido em **PostgreSQL**.
6. Processamento assíncrono: a API responde `202 Accepted` com `task_id`, e o enriquecimento acontece em background.

### 3.2 Fluxo de Entrada — Instituição

1. A instituição descreve a necessidade em linguagem natural (ex.: *"Enchente atingiu nosso abrigo, precisamos de equipe médica e ajuda para resgatar idosos"*).
2. O **Orchestrate** aciona `POST /api/v1/necessidades`.
3. Processo idêntico ao do voluntário: o watsonx.ai transforma a dor em requisitos técnicos (habilidades, nível de urgência, contexto).
4. A demanda é salva na tabela `necessidades`.

### 3.3 Fluxo de Matchmaking (O Vínculo)

1. **Gatilho automático** quando `urgencia = crítico`: um evento é enfileirado e dispara o matching imediatamente.
2. **Gatilho manual** via `POST /api/v1/vinculos` executado pelo Orchestrate (ou por um coordenador).
3. A API executa uma **consulta inteligente** combinando:
   - Correspondência semântica de habilidades (taxonomia normalizada).
   - Distância geográfica (Haversine no MVP, PostGIS `ST_DWithin` em produção).
   - Reputação do voluntário (histórico de feedbacks).
   - Fadiga (penalização para quem foi acionado recentemente, anti-burnout).
4. O Orchestrate apresenta os top-N voluntários ranqueados e **notifica-os em paralelo**.
5. O voluntário aceita ou recusa via `POST /api/v1/vinculos/{id}/aceitar` ou `/recusar`.
6. Ao final, feedback estruturado via `POST /api/v1/vinculos/{id}/feedback` realimenta o ranking.

---

## 4. Stack Tecnológica

| Camada | Tecnologia | Papel |
|---|---|---|
| **Interface/Agente** | IBM watsonx Orchestrate | Orquestração de Skills e fluxos de negócio |
| **Cérebro de IA** | watsonx.ai (Granite) | Extração de habilidades, normalização, inferência |
| **Backend** | Python 3.11 + FastAPI 0.111 | Regras de negócio e contrato OpenAPI |
| **ORM** | SQLAlchemy 2.0 | Camada de persistência |
| **Banco de Dados** | PostgreSQL 15 + PostGIS *(opcional)* + pgvector *(opcional)* | Armazenamento relacional + consultas geoespaciais + embeddings |
| **Cache** | Redis *(recomendado)* | Cache de geocoding e normalização de skills |
| **Fila** | FastAPI BackgroundTasks (MVP) → Celery/RabbitMQ (produção) | Processamento assíncrono |
| **Infraestrutura** | Docker Compose (dev) → IBM Cloud (prod) | Containerização e deploy |
| **Observabilidade** | Logs JSON estruturados + métricas Prometheus + dashboards Grafana | Monitoramento e auditoria |

---

## 5. Modelo de Dados

### Tabelas principais

**`voluntarios`**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `nome` | string | |
| `telefone` | string | Criptografado em repouso |
| `email` | string | |
| `relato_original` | text | Texto bruto enviado pelo voluntário |
| `habilidades` | string[] | Normalizadas contra a taxonomia |
| `latitude` / `longitude` | float | Geocodificadas |
| `disponibilidade` | enum | `disponivel`, `ocupado`, `em_missao`, `inativo` |
| `ultima_missao_em` | timestamp | Para cálculo de fadiga |
| `reputacao` | float | Score de 0 a 5 agregado de feedbacks |
| `consentimento_lgpd` | bool | Consentimento explícito registrado |
| `criado_em` / `atualizado_em` | timestamp | |

**`necessidades`**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `instituicao_id` | UUID | FK para `instituicoes` |
| `descricao_crise` | text | Relato original |
| `habilidades_requeridas` | string[] | Normalizadas |
| `latitude` / `longitude` | float | Geocodificadas |
| `nivel_urgencia` | enum | `baixo`, `medio`, `alto`, `critico` |
| `status` | enum | `aberta`, `em_atendimento`, `resolvida`, `cancelada` |
| `criado_em` | timestamp | |

**`instituicoes`**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `nome` | string | |
| `cnpj` | string | Validado |
| `verificada` | bool | Aprovação manual |
| `contato` | jsonb | Multi-canal (email, telefone, WhatsApp) |

**`vinculos`** — *a entidade que faltava no desenho inicial*

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `necessidade_id` | UUID | FK |
| `voluntario_id` | UUID | FK |
| `status` | enum | `proposto`, `aceito`, `recusado`, `em_atendimento`, `concluido`, `cancelado` |
| `score_match` | float | Score calculado no momento do match |
| `proposto_em` / `aceito_em` / `concluido_em` | timestamp | Audit trail |

**`feedbacks`**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `vinculo_id` | UUID | FK |
| `voluntario_compareceu` | bool | |
| `skill_adequada` | bool | |
| `nota` | int | 1 a 5 |
| `comentario` | text | |

**`skills_taxonomia`**

| Campo | Tipo | Observação |
|---|---|---|
| `codigo` | string | PK (ex.: `saude.primeiros_socorros`) |
| `label` | string | Nome amigável |
| `categoria` | string | `saude`, `resgate`, `logistica`, `psicossocial`, etc. |
| `sinonimos` | string[] | Termos que o Granite deve mapear para este código |

**`eventos_pendentes`** — fila simples sem depender de Kafka

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `tipo` | enum | `necessidade_critica`, `match_criado`, `feedback_recebido` |
| `payload` | jsonb | |
| `processado` | bool | |
| `criado_em` | timestamp | |

---

## 6. Contratos da API (OpenAPI)

### Rotas principais

| Método | Rota | Função |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/v1/voluntarios` | Cadastrar voluntário (extração via Granite) |
| `GET` | `/api/v1/voluntarios/{id}` | Consultar perfil |
| `PATCH` | `/api/v1/voluntarios/{id}` | Atualizar perfil ou disponibilidade |
| `POST` | `/api/v1/necessidades` | Registrar demanda crítica |
| `GET` | `/api/v1/necessidades` | Listar demandas (filtros por status/urgência) |
| `POST` | `/api/v1/vinculos` | Executar matchmaking (cria proposta de vínculo) |
| `GET` | `/api/v1/vinculos/{id}` | Consultar status de um vínculo |
| `POST` | `/api/v1/vinculos/{id}/aceitar` | Voluntário aceita |
| `POST` | `/api/v1/vinculos/{id}/recusar` | Voluntário recusa |
| `POST` | `/api/v1/vinculos/{id}/concluir` | Registrar conclusão |
| `POST` | `/api/v1/vinculos/{id}/feedback` | Enviar feedback pós-atendimento |
| `GET` | `/api/v1/estatisticas` | Métricas agregadas (para pitch e dashboards) |

### Correções em relação ao desenho inicial

- **`GET /matchmaking` vira `POST /vinculos`.** Matchmaking tem efeito colateral (cria registro, dispara notificações), portanto não é idempotente nem adequado para GET.
- **Processamento assíncrono:** cadastros retornam `202 Accepted` com `task_id`, e `GET /tasks/{task_id}` permite consultar o progresso.

---

## 7. Algoritmo de Matchmaking

### Score composto

```
score = α · similaridade_skill
      + β · proximidade
      + γ · reputação
      + δ · disponibilidade_recente
```

### Pesos ajustáveis por urgência

| Urgência | α (skill) | β (proximidade) | γ (reputação) | δ (disponibilidade) |
|---|---|---|---|---|
| `crítico` | 0.25 | **0.50** | 0.15 | 0.10 |
| `alto` | 0.35 | 0.35 | 0.20 | 0.10 |
| `médio` | 0.45 | 0.25 | 0.20 | 0.10 |
| `baixo` | 0.50 | 0.20 | 0.20 | 0.10 |

**Raciocínio:** quanto mais crítica a situação, mais peso a proximidade ganha — em enchente, o voluntário que chega em 15 minutos vale mais que o especialista a 40 km.

### Correspondência semântica de habilidades

Duas estratégias, da mais simples à mais ambiciosa:

1. **MVP — taxonomia controlada.** Durante o cadastro, o Granite classifica o relato contra a lista de `skills_taxonomia`. Match vira operação de interseção de conjuntos — determinística, rápida, fácil de demonstrar e debugar.
2. **Evolução — embeddings vetoriais.** `pgvector` no Postgres + embeddings do watsonx.ai. Voluntário e necessidade viram vetores; o match é `cosine similarity`. Elegante e mais rico, mas requer validação extra.

### Anti-burnout (penalização de fadiga)

Voluntários acionados nas últimas 72h sofrem penalização gradual no score. Sustentabilidade humana é requisito, não detalhe.

### Diversidade nas recomendações

Evitar sempre o mesmo top-3. Pequeno componente de aleatoriedade controlada garante rotação da base.

---

## 8. Diagrama Lógico

```
                          ┌──────────────────────┐
                          │  Canais de Entrada   │
                          │ (Web, WhatsApp, SMS) │
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │ watsonx Orchestrate  │  ← Skills (OpenAPI)
                          │  (maestro + Skills)  │
                          └─────┬────────┬───────┘
                                │        │
                  ┌─────────────▼──┐  ┌──▼──────────────┐
                  │   FastAPI      │  │  Notificação    │
                  │   (músculo)    │  │ (WhatsApp/SMS)  │
                  └──┬──────┬──────┘  └─────────────────┘
           async ↓   │      │ ↓ enrich
      ┌────────────┐ │      │ ┌────────────────────────┐
      │ Fila/Worker│ │      │ │ watsonx.ai (Granite)   │
      │ (bg tasks) │ │      │ │ - extração skills      │
      └─────┬──────┘ │      │ │ - normalização         │
            │        │      │ │ - embeddings (opt.)    │
            ▼        ▼      ▼ └────────────────────────┘
      ┌─────────────────────────┐   ┌──────────────────┐
      │ PostgreSQL + PostGIS    │   │ Redis (cache)    │
      │ + pgvector (opcional)   │   │ - geocoding      │
      │ tabelas:                │   │ - skill norm.    │
      │  voluntarios            │   └──────────────────┘
      │  necessidades           │
      │  instituicoes           │
      │  vinculos      ← NOVA   │
      │  feedbacks     ← NOVA   │
      │  skills_taxonomia ← NOVA│
      │  eventos_pendentes      │
      └─────────────────────────┘
                  │
                  ▼
      ┌─────────────────────────┐
      │ Observabilidade         │
      │ (logs JSON + métricas)  │
      └─────────────────────────┘
```

---

## 9. Resiliência, Segurança e LGPD

### Resiliência

- **Fallback determinístico** para quando o watsonx.ai estiver lento ou indisponível: extração baseada em keywords contra a taxonomia.
- **Retry com backoff exponencial** em todas as chamadas externas (watsonx.ai, geocoding, notificação).
- **Circuit breaker** para evitar cascata de falhas.
- **Processamento assíncrono:** o cadastro nunca bloqueia o usuário esperando o LLM.

### Segurança

- **Autenticação:** JWT para coordenadores e instituições; token de uso único para voluntários aceitarem/recusarem.
- **Verificação de instituições:** validação de CNPJ + aprovação manual assíncrona. Sem isso, qualquer um pescaria telefones de voluntárias.
- **Rate limiting** nas rotas de cadastro e matchmaking.
- **Criptografia em repouso** para `telefone` e `email`.

### LGPD

- **Consentimento explícito** registrado no cadastro (`consentimento_lgpd = true`).
- **Minimização:** antes do match ser aceito, a instituição vê apenas iniciais + distância aproximada — nunca telefone direto.
- **Log de acesso** (quem acessou quais dados e quando).
- **Direito ao esquecimento:** endpoint `DELETE /api/v1/voluntarios/{id}` com exclusão efetiva + anonimização de logs.

---

## 10. Observabilidade

- **Logs estruturados em JSON** com `correlation_id` propagado desde o Orchestrate.
- **Métricas essenciais:**
  - `matches_criados_total`
  - `tempo_medio_ate_aceite_segundos`
  - `taxa_aceite_voluntarios`
  - `latencia_watsonx_ai_ms`
  - `taxa_sucesso_geocoding`
- **Dashboard Grafana** com 3 painéis mínimos: volume operacional, latências, saúde das integrações externas.
- **Audit trail LGPD** separado do log operacional.

---

## 11. Roadmap Priorizado para o Hackathon

Com equipe de 4 pessoas e tempo limitado, a priorização é essencial.

### Must-have (Dias 1–2) — sem isso não há demo

- [ ] Models SQLAlchemy: `voluntarios`, `necessidades`, `vinculos`, `skills_taxonomia`.
- [ ] Geocodificação simples de endereços (uma chamada externa) e armazenamento de lat/lng.
- [ ] Extração de skills com Granite normalizando contra taxonomia fixa (sem embeddings).
- [ ] Matching por interseção de habilidades + distância Haversine em SQL puro.
- [ ] Endpoints: `POST /voluntarios`, `POST /necessidades`, `POST /vinculos`, `POST /vinculos/{id}/concluir`.
- [ ] Endpoint de feedback mínimo.
- [ ] Swagger rico para o Orchestrate consumir.

### Should-have — para impressionar a banca

- [ ] Fluxo assíncrono com `202 Accepted` + `task_id`.
- [ ] Painel simples (Streamlit ou HTML) mostrando demandas abertas e matches feitos.
- [ ] Fallback quando watsonx.ai falhar.
- [ ] PostGIS se sobrar tempo.
- [ ] Estatísticas agregadas para o pitch (`GET /estatisticas`).

### Nice-to-have — roadmap para o pitch

- [ ] `pgvector` + embeddings semânticos do watsonx.ai.
- [ ] Notificação multi-canal (WhatsApp Business API).
- [ ] Dashboard Grafana.
- [ ] Verificação de CNPJ automatizada.

---

## 12. Narrativa para o Pitch

A arquitetura tem um diferencial narrativo que vale enfatizar: **a solução transforma linguagem humana em coordenação estruturada**. Em crise, ninguém preenche formulário. A solução remove essa barreira dos dois lados simultaneamente — voluntário e instituição falam em linguagem natural, e o Granite traduz para ação.

O **watsonx Orchestrate** não é só um barramento de APIs. Ele é o **idioma comum entre a dor e a competência**. O loop se fecha com o feedback pós-atendimento, que transforma a solução em um sistema que **aprende com cada crise que atende** — não apenas um serviço de recomendação ingênuo.

Três métricas de impacto para o pitch:

1. **Tempo médio entre chegada da demanda crítica e primeiro voluntário aceito.**
2. **Taxa de resolução de demandas em até 2 horas.**
3. **Índice de satisfação pós-atendimento.**

---

## 13. Equipe

- Gabriel Yoshino
- Lais Gonçalves
- Mateus Alves
- Vitor Bueno

---

*Documento vivo — atualizado conforme a implementação evolui.*
