# Notas de Pitch — Crise-Sync

> **Hackathon UNASP + IBM 2026 — "Voluntariado Inteligente para Crises"**
> Documento-cola para a apresentação e a arguição.
> Última atualização: **2026-04-27**.

---

## 1. Pitch em 30 segundos

> Em uma enchente, ninguém preenche formulário. A instituição **descreve a crise em linguagem natural** no chat do watsonx Orchestrate, o **watsonx.ai (Granite)** extrai habilidades e urgência, nosso backend FastAPI executa um **matchmaking ponderado** (skill + distância + reputação + anti-burnout) e o Orchestrate notifica os top‑N voluntários em paralelo. Quem aceitar primeiro recebe o contato. O feedback pós-atendimento realimenta a reputação. **Loop agêntico fechado.**

---

## 2. Tese central

A barreira do voluntariado em crise **não é falta de gente** — é **fricção operacional** no momento mais crítico. Catálogos manuais e formulários longos são o que separam um voluntário pronto de uma família resgatada.

Crise-Sync **remove a fricção em três pontos**:

1. **Entrada** — o relato substitui o formulário (LLM → schema).
2. **Decisão** — o algoritmo substitui o ctrl-F na planilha (composite score).
3. **Loop** — a reputação substitui o "quem é bom mesmo?" (feedback realimenta).

---

## 3. Arquitetura em uma frase

**Frontend estático** (Tailwind + Lucide) → **FastAPI** (Python 3.11, SQLAlchemy 2.0 ORM) → **Postgres 15** + **watsonx.ai (Granite)** para IA → **watsonx Orchestrate** consome o OpenAPI como **Skill** e fala com o usuário.

```
[Coordenador no Chat]
        │ (linguagem natural)
        ▼
[watsonx Orchestrate Agent] ─── Skill (OpenAPI) ───▶ [FastAPI / Crise-Sync]
                                                              │
                                                              ├── watsonx.ai Granite (extrai skills)
                                                              ├── PostgreSQL (estado)
                                                              └── algoritmo de matchmaking
```

**Por que essa stack?**

- **FastAPI**: tipagem forte, OpenAPI grátis (Orchestrate consome direto, sem adapter), async nativo para chamadas IA não-bloqueantes.
- **Postgres**: ACID em fluxo de "aceitou primeiro ganha". Roadmap PostGIS/pgvector.
- **Granite (watsonx.ai)**: foundation model com fallback determinístico se cair (degradação graciosa).
- **Orchestrate**: o usuário não muda de aplicativo — fala onde já trabalha.
- **Docker Compose + GitHub Actions**: deploy reproduzível, push em `main` → produção em ~30s.

---

## 4. Demo — roteiro ao vivo

> Tudo rodando em **http://192.241.151.209:8000** (VPS, com auto-deploy desde `main`).

| Passo | Ação | O que mostrar |
|---|---|---|
| 0 | Abrir `/painel` | KPIs zerados, badge ONLINE |
| 1 | `POST /api/v1/dev/seed-voluntarios-exemplo` | 15 voluntários em SP |
| 2 | No chat do Orchestrate: _"Enchente atingiu nosso abrigo em Vila Nova. Precisamos urgente de médico para idosos e ajuda no resgate."_ | Skill cria a necessidade; Granite extrai `medico.*`, `resgate.*`, urgência `critica` |
| 3 | `POST /api/v1/vinculos { necessidade_id, top_n: 3 }` | Top‑3 com `score_match`, `distancia_km`, `habilidades_correspondentes`, `justificativa` (texto humano) |
| 4 | `POST /api/v1/vinculos/{id}/aprovar` → `/aceitar` | Voluntário recebe contato; demais propostas são canceladas |
| 5 | `POST /api/v1/vinculos/{id}/concluir` + `/feedback {nota: 5}` | Reputação sobe via média móvel — fecha o loop |

**Plano B se a internet cair:** o painel já está aberto e o `IAFallbackKeywords` gera a justificativa local sem chamar Granite.

---

## 5. O algoritmo de matchmaking (conteúdo de arguição)

Score composto em `[0, 1]`:

```
score = α·skill + β·proximidade + γ·reputação + δ·disponibilidade
```

**Pesos por urgência** (`app/services/matching.py` → `PESOS_POR_URGENCIA`):

| Urgência | α (skill) | β (prox.) | γ (reputação) | δ (disponib.) |
|---|---|---|---|---|
| `critica` | 0.30 | **0.50** | 0.10 | 0.10 |
| `alta` | 0.40 | 0.35 | 0.15 | 0.10 |
| `media` | 0.45 | 0.25 | 0.20 | 0.10 |
| `baixa` | 0.50 | 0.15 | 0.25 | 0.10 |

**Por que mexer nos pesos por urgência?** Em crítica, **chegar rápido importa mais que ter o currículo perfeito** — um socorrista a 1km com skill parcial ganha de um especialista a 30km. Em baixa, o oposto.

**Componentes:**

- `skill`: razão de skills da necessidade que o voluntário cobre — taxonomia hierárquica permite match parcial (`medico.urgencia` cobre `medico.*`).
- `proximidade`: Haversine → exponencial decrescente (`exp(-d/raio)`), `raio` varia por urgência.
- `reputação`: média de feedbacks (escala 1–5) normalizada, soft-start com 3.0.
- `disponibilidade`: 0 se `em_missao`, penalização anti-burnout (72h da última missão).

**Empate:** menor distância vence. É o `recomendado: true` na resposta.

---

## 6. Por que IA aqui (e não regex)

| Tarefa | Sem LLM | Com Granite |
|---|---|---|
| Extrair skills do relato | Lista de palavras-chave; falha em sinônimos, contexto, idioma | Mapeia para a taxonomia mesmo em frases ambíguas |
| Estimar urgência | Heurística manual frágil | Considera tom, escala ("famílias ilhadas") e gravidade |
| Justificar a recomendação para a instituição | Template fixo | Texto curto contextual ("aderente porque..., próxima a...") |

**Mas IA pode falhar.** Por isso temos `IAFallbackKeywords` — extrator determinístico de keywords contra a `SKILLS_TAXONOMIA`. Hoje o pipeline é **triplo**:

1. `IAWatsonxService` (Granite via `httpx` + IAM token)
2. `IAFallbackKeywords` (local, sem rede)
3. String fixa final ("Recomendado pelo algoritmo com base em skills, proximidade e reputação")

Resultado: **a UX do painel nunca quebra**, mesmo com Granite indisponível.

---

## 7. Privacidade & LGPD

- Telefone e endereço **só são expostos depois do `aceito`** (status do vínculo).
- Antes disso, a instituição vê **iniciais + skills + score + distância**.
- Senha temporária válida por **2h**, hash bcrypt, troca obrigatória no primeiro login (`precisa_trocar_senha`).
- Login_id = primeiros 8 chars do UUID — não revela ID interno completo.
- Consentimento explícito no cadastro (campo `consentimento_lgpd`).

---

## 8. Roadmap pós-hackathon (frase pronta)

- **Geo no banco**: PostGIS + índices GIST → KNN nativo (hoje pré-filtramos por bounding box e calculamos Haversine na app).
- **Embeddings de skills**: pgvector para skills livres ("operador de drone florestal") sem precisar atualizar a taxonomia.
- **Multi-tenant**: cada instituição com seu pool e seu coordenador.
- **Push real**: Orchestrate dispara WhatsApp/SMS via canal dedicado em vez de só notificar no chat.
- **Observabilidade**: OpenTelemetry → Grafana, alerta em `score_p50` derretendo.

---

## 9. Perguntas-zumbi (e como matar)

> **"E se dois voluntários aceitarem ao mesmo tempo?"**
> O `aceitar` é uma transação Postgres com check de status — quem aceitar primeiro vira `aceito`, os demais propostos para a mesma necessidade são `cancelados` no mesmo commit. Sem race.

> **"Como vocês evitam que o melhor voluntário seja chamado toda hora?"**
> Penalidade anti-burnout: voluntário que terminou missão nas últimas 72h ganha δ menor. Quem cumpriu missão hoje cai no ranking amanhã. Equidade automática.

> **"Se a Granite estiver fora, o sistema cai?"**
> Não. `get_ia_service()` retorna `IAFallbackKeywords` quando `WATSONX_API_KEY` falta; mesmo com Granite configurado, qualquer exceção cai no fallback local e depois numa string fixa. Justificativa nunca volta `null` para o frontend.

> **"Por que FastAPI e não Flask/Express?"**
> OpenAPI gerado automaticamente — o Orchestrate importa direto como Skill, **zero adapter manual**. Pydantic v2 valida payloads no boundary, async libera o thread enquanto Granite responde.

> **"O painel está hardcoded em ngrok?"**
> Não mais. `api-config.js` resolve a URL na ordem `localStorage` → `<meta>` → `window.location.origin` → fallback VPS. Funciona aberto direto pelo `file://`, servido pelo FastAPI ou em qualquer host.

> **"Como vocês fizeram deploy?"**
> Push em `main` dispara GitHub Actions → SSH na VPS → `git reset --hard origin/main` → `docker compose up -d --build` → health check em `/health`. Rollback é commit-revert.

> **"E se a taxonomia não cobrir uma skill nova?"**
> Hoje cai no fallback de keywords (substring match) e ainda assim retorna **algo**. Roadmap: pgvector permite skill livre por similaridade semântica sem mexer na taxonomia.

---

## 10. Métricas que importam (caso perguntem KPI)

- **Tempo do relato ao primeiro `aceito`** — alvo P50 < 5min.
- **% de necessidades resolvidas em < 1h** em urgência crítica.
- **Cobertura de skills** = `len(habilidades_correspondentes) / len(habilidades_necessarias)`.
- **Reuso saudável** — % de voluntários ativos no mês / total cadastrado.
- **Burnout** — % de aceites por voluntário acima de N missões/semana.

---

## 11. Equipe e divisão (se perguntarem)

- **Mateus** — backend FastAPI, banco, deploy, integração Orchestrate.
- **Vitor** — watsonx.ai (extração de skills via Granite, prompts).
- **Gabriel** — watsonx Orchestrate (Skill, agente, fluxo de chat).

---

## 12. Slogan de fechamento

> **Crise-Sync: a IA não substitui o voluntário — ela tira a fricção entre o relato e a chegada de quem ajuda.**
