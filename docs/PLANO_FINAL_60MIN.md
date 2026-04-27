# Plano Final — Crise-Sync (60 minutos para entrega)

> Hackathon UNASP + IBM 2026 — consolidação técnica + melhorias seguras + arquitetura agêntica.
> Premissa: **não quebrar o que já funciona**. Tudo abaixo é triado por risco × impacto × tempo.

---

## 1. Diagnóstico — o que já está sólido

| Camada | Estado | Comentário curto |
|---|---|---|
| FastAPI 0.111 + SQLAlchemy 2 | ✅ Pronto | 32 endpoints, tags semânticas, OpenAPI rico em descrições. |
| Taxonomia controlada (24 skills) | ✅ Pronto | Boa, hierárquica (`saude.enfermagem`, `resgate.aquatico`). |
| Matchmaking ponderado por urgência | ✅ Pronto | α/β/γ/δ por urgência + anti-burnout 72h. |
| Pipeline IA com 3 níveis de fallback | ✅ Pronto | `IAWatsonxService` → `IAFallbackKeywords` → string fixa. **Argumento forte de pitch.** |
| Frontend `api-config.js` resolvendo origin | ✅ Pronto | `localStorage` → `<meta>` → `window.location.origin` → VPS. |
| Auto-deploy GitHub Actions → VPS | ✅ Pronto | Push em `main` → ~30s prod. |
| LGPD: contato exposto só após `aceito` | ✅ Pronto | Iniciais + skills + score + distância antes do aceite. |
| Pitch notes (`docs/PITCH_NOTES.md`) | ✅ Pronto | Roteiro de demo + perguntas-zumbi. |

**Veredito:** o backend está em estado de demo. O risco real está **fora do código** — na camada do Orchestrate (configuração do agente).

---

## 2. O verdadeiro gargalo — anti-pattern do agente único

### Sintoma
Vocês carregaram **as 32 tools no mesmo agente `oss 120b`**.

### Por que isso degrada o agente
- **Janela de contexto poluída.** A descrição de cada tool (parâmetros, exemplos, tags) entra no system prompt; com 32 tools, o modelo gasta atenção decidindo *qual* chamar antes de pensar no conteúdo.
- **Confusão semântica.** Tools muito parecidas (ex.: `aceitar`, `aprovar`, `recusar`, `rejeitar`) competem entre si. O `oss 120b` é capaz, mas não é o `Granite-3-8b-instruct` ou o `Llama-3.3-70b` em *function-calling*.
- **Loop ineficiente.** Quando o agente erra a tool, ele re-tenta — em demo ao vivo isso é fatal.
- **Difícil de explicar na arguição.** “Um agente com 32 tools” soa como protótipo. **“Um maestro orquestrando 4 sub-agentes especializados”** soa como arquitetura.

### Decisão recomendada
**Manter o `oss 120b`** (já está funcionando, custo zero de troca) **e dividir as tools por papel de negócio**, criando o pattern *Maestro + Skill Agents*. Sem trocar modelo, sem mexer no backend.

---

## 3. Arquitetura agêntica recomendada (sem reescrever nada)

```
                  ┌────────────────────────┐
                  │   AGENTE MAESTRO       │  oss 120b
                  │  "Coordenador Crise"   │  ← chat com o usuário
                  └──┬──────┬──────┬───────┘
                     │      │      │
           routes →  │      │      │  ← agentes invocados como ferramentas
                     ▼      ▼      ▼
        ┌────────────┐  ┌──────────┐  ┌─────────────────┐  ┌──────────────┐
        │ Cadastro   │  │ Triagem  │  │ Matchmaking     │  │ Pós-Atendim. │
        │ Agent      │  │ Agent    │  │ & Decisão Agent │  │ Agent        │
        └────────────┘  └──────────┘  └─────────────────┘  └──────────────┘
        - voluntários    - necessid.   - vínculos          - concluir
        - instituições   - urgência    - aprovar/rejeitar  - feedback
        - verificar      - regiões     - aceitar/recusar   - estatísticas
```

### Como atribuir as 32 tools (cole no Orchestrate)

| Sub-agente | Tools (endpoints) | Papel |
|---|---|---|
| **Cadastro Agent** | `POST /voluntarios`, `GET/PATCH /voluntarios/{id}`, `GET /voluntarios/verificar`, `POST /instituicoes`, `GET/PATCH/DELETE /instituicoes/{id}`, `GET /instituicoes/verificar`, `POST /auth/login`, `POST /auth/trocar-senha` | Onboarding e gestão de cadastro. |
| **Triagem Agent** | `POST /necessidades`, `GET /necessidades`, `GET /necessidades/{id}`, `GET /instituicoes/regioes`, `GET /instituicoes/{id}/necessidades` | Recebe o relato da crise, dispara enriquecimento Granite, lista demandas. |
| **Matchmaking Agent** | `POST /vinculos`, `GET /vinculos/{id}`, `GET /vinculos/pendentes`, `POST /vinculos/{id}/aprovar`, `POST /vinculos/{id}/rejeitar`, `POST /vinculos/{id}/aceitar`, `POST /vinculos/{id}/recusar`, `GET /vinculos/voluntario/{id}` | Executa o match e gerencia o ciclo de aceite. |
| **Pós-Atendimento Agent** | `POST /vinculos/{id}/concluir`, `POST /vinculos/{id}/feedback`, `GET /estatisticas` | Fecha o loop agêntico (feedback → reputação → próximo match). |
| _(Apenas no Maestro)_ | `POST /dev/seed-voluntarios-exemplo`, `DELETE /dev/reset` | Mantenha **só** no maestro e oculte da apresentação. |

### Por que essa divisão funciona
- Cada sub-agente recebe **≤ 8 tools** — janela respira, escolha de tool fica trivial.
- Os nomes batem 1-para-1 com o **fluxo agêntico do `ARCHITECTURE.md`** (Cadastro → Triagem → Matchmaking → Loop). Você narra a arquitetura mostrando o painel do Orchestrate.
- Maestro decide *qual sub-agente acionar* a partir de uma frase do usuário — função muito mais simples do que escolher 1 entre 32 tools.

### Tempo estimado
- ~15 min para criar 4 sub-agentes no Orchestrate, colar a OpenAPI parcial em cada um e ajustar a descrição.
- ~10 min para testar o fluxo de demo ponta-a-ponta.

---

## 4. Prompts canônicos para os agentes (cole pronto)

### 4.1 Maestro — “Coordenador Crise”

```
Você é o Coordenador da Crise-Sync, um sistema de voluntariado em emergências.
Seu papel é entender a intenção do usuário e delegar para o sub-agente correto.

Sub-agentes disponíveis:
  • Cadastro Agent — quando o usuário fala em CADASTRAR, ATUALIZAR, VERIFICAR
    voluntário ou instituição, ou em LOGIN/SENHA.
  • Triagem Agent — quando o usuário descreve UMA CRISE, uma DEMANDA, um
    PEDIDO de ajuda em linguagem natural ("a água subiu", "preciso de
    médico", "tem família ilhada").
  • Matchmaking Agent — quando se fala em ENCONTRAR voluntários, AVALIAR
    candidatos, APROVAR/REJEITAR sugestões, ou quando o voluntário ACEITA/
    RECUSA uma missão.
  • Pós-Atendimento Agent — quando o atendimento ENCERRA, há FEEDBACK, ou
    pede MÉTRICAS/ESTATÍSTICAS.

Regras:
1. Em DÚVIDA, faça UMA pergunta curta antes de delegar.
2. Nunca exponha telefone/email do voluntário antes de o vínculo estar `aceito`.
3. Em situação CRÍTICA (palavras: enchente, ilhado, desabamento, "agora"),
   priorize Triagem → Matchmaking sem confirmar.
4. Responda sempre em português, em frases curtas.
```

### 4.2 Triagem Agent (o mais importante para a demo)

```
Você é o agente de Triagem da Crise-Sync.
Quando receber um relato de crise:
1. Chame `POST /api/v1/necessidades` com o relato BRUTO no campo
   `descricao_crise`. NÃO reformule, NÃO resuma — o Granite no backend extrai
   skills e urgência a partir do texto original.
2. Se o usuário não disse o endereço, pergunte UMA vez: "Qual o endereço da
   ocorrência?". Se houver lat/lng, use; senão, mande só o endereço.
3. Após criar a necessidade (status 202), responda: "Triagem registrada.
   Posso buscar voluntários agora?" — e, ao "sim", delegue para o
   Matchmaking Agent passando o `resource_id`.

Nunca invente skills nem nível de urgência — quem decide isso é o backend.
```

### 4.3 Matchmaking Agent

```
Você é o agente de Matchmaking.
Ao receber `necessidade_id`:
1. Chame `POST /api/v1/vinculos` com `top_n: 3`.
2. Apresente os candidatos com: iniciais, score (0-1), distância em km,
   habilidades correspondentes e a JUSTIFICATIVA já vinda do backend.
   NÃO invente justificativa — repita a recebida.
3. Aguarde a instituição APROVAR um candidato → chame `/aprovar`.
4. Quando o voluntário aceitar pelo painel, confirme com o coordenador.

Se a instituição rejeitar todos, retorne para Triagem para reabrir busca.
```

### 4.4 Pós-Atendimento Agent

```
Você é o agente de Pós-Atendimento.
Fluxo:
1. Receber confirmação de atendimento concluído → `/concluir`.
2. Coletar feedback estruturado: `voluntario_compareceu` (bool),
   `skill_adequada` (bool), `nota` (1-5) e comentário opcional.
3. Confirmar que a reputação foi atualizada — explique em uma frase que
   isso influencia matches futuros (LOOP AGÊNTICO).
4. Se pedirem métricas, chame `/estatisticas`.
```

---

## 5. Plano de execução — 60 minutos cronometrados

> Trabalhe em paralelo. Mateus + Vitor + Gabriel + Lais cada um numa frente.

### ⏱ 0–10 min — Validação rápida
- [ ] `curl http://192.241.151.209:8000/health` deve retornar `{ok}`.
- [ ] Abrir `/painel` e rodar `seed-voluntarios-exemplo` no Swagger.
- [ ] Conferir que `justificativa` nunca volta `null` (já testado no `CHANGELOG_2026-04-27.md`).
- [ ] Conferir que `script-index.js` está consumindo `window.MATCHHELP_API`.

### ⏱ 10–35 min — Multi-agente no Orchestrate **(maior ganho)**
- [ ] **Gabriel:** criar 4 sub-agentes no Orchestrate seguindo a tabela da Seção 3.
- [ ] Cada sub-agente recebe **só** a fração da OpenAPI relevante (no Orchestrate, tools podem ser filtradas por tag — use `Voluntários,Instituições,Autenticação` para o Cadastro Agent, `Necessidades` para Triagem, `Vínculos` para Matchmaking, `Vínculos,Estatísticas` para Pós-Atendimento).
- [ ] Maestro `Coordenador Crise` recebe **só os 4 sub-agentes como tools**, sem nenhum endpoint direto (exceto seed/reset, escondidos).
- [ ] Colar os prompts da Seção 4 em cada agente.
- [ ] Testar: digitar “Enchente atingiu meu abrigo em Vila Nova, preciso de médico para idosos”.

### ⏱ 35–45 min — Polimento de Watson.ai (Vitor) — **opcional, sem risco**
- [ ] Confirmar que `IA_PROVIDER=watsonx` está setado na VPS via `.env`.
- [ ] Se o Granite estiver respondendo lento (>3s), **deixar como está** — o fallback de keywords salva a demo.
- [ ] **NÃO trocar de modelo agora.** `granite-3-8b-instruct` é o padrão do `.env.example`. Trocar para 3.3-70b custa tempo de teste sem ganho proporcional para a demo.

### ⏱ 45–55 min — Ensaio do roteiro de demo
- [ ] Seguir o roteiro do `docs/PITCH_NOTES.md` Seção 4 — ele já tem 6 passos.
- [ ] Treinar 2 vezes ponta-a-ponta. Cronometrar.
- [ ] Plano B: se Orchestrate cair, demonstrar o mesmo fluxo via Swagger UI (`/docs`) — **garante que vocês defendem o backend mesmo se o agente quebrar**.
- [ ] Ter aberta uma aba com `/painel` mostrando os matches em tempo real.

### ⏱ 55–60 min — Buffer
- [ ] Commit final com mensagem `docs: plano final + arquitetura multi-agente`.
- [ ] Push → CI deploya → bate `/health` → respira.

---

## 6. O que **NÃO** fazer agora (controle de risco)

| Tentação | Por que evitar |
|---|---|
| Trocar `oss 120b` por outro modelo | Risco de regressão > ganho. O bottleneck é a divisão de tools, não o modelo. |
| Adicionar PostGIS / pgvector | Roadmap pós-hackathon. Mexer em DB a 1h da entrega = suicídio. |
| Refatorar OpenAPI | Já está rico. Tags por domínio funcionam para o Orchestrate filtrar. |
| Mudar autenticação | JWT/login_id está testado. Não tocar. |
| Implementar WhatsApp/SMS real | É uma frase no roadmap, não na demo. |
| Refazer o painel | `api-config.js` resolveu o problema do ngrok. Está bom. |

---

## 7. Arguição — frases prontas para a banca

> **“Por que vocês usam vários agentes em vez de um só?”**
> Cada sub-agente tem uma fronteira de responsabilidade clara — Cadastro, Triagem, Matchmaking, Pós-Atendimento. Isso reduz o espaço de decisão de cada agente, melhora a precisão de tool-calling e espelha exatamente o fluxo agêntico documentado na arquitetura.

> **“Por que o `oss 120b` e não Granite?”**
> O `oss 120b` é o orquestrador — ele só decide *qual sub-agente chamar*. A inteligência específica de domínio (extrair skill, classificar urgência) está no `granite-3-8b-instruct` invocado pelo backend FastAPI. Cada modelo no papel certo.

> **“Como o sistema aprende?”**
> Loop fechado: o feedback pós-atendimento atualiza a reputação do voluntário, que entra como variável γ no score composto. Cada crise que atendemos calibra os matches futuros.

> **“E se o Orchestrate cair?”**
> A API é totalmente operável via Swagger UI ou cURL. O agente é a camada de UX, não a fonte da verdade.

> **“E se o Granite cair?”**
> Pipeline de degradação em 3 níveis — Watsonx.ai Granite → fallback de keywords contra a taxonomia → string fixa. O usuário nunca vê erro.

---

## 8. Checklist final antes de entrar no palco

- [ ] `/health` retorna 200 (`curl -fsS http://192.241.151.209:8000/health`).
- [ ] `/painel` abre e mostra badge ONLINE.
- [ ] Seed dos 15 voluntários está aplicado.
- [ ] Os 4 sub-agentes do Orchestrate respondem ao Maestro.
- [ ] Demo de 3 minutos foi cronometrada.
- [ ] Plano B (Swagger) está aberto numa aba.
- [ ] Slogan na ponta da língua: **“A IA não substitui o voluntário — ela tira a fricção entre o relato e a chegada de quem ajuda.”**

---

*Boa sorte. O projeto está mais maduro do que parece — confiem na arquitetura.*
