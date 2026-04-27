# Changelog — 2026-04-27 (sprint final pré-pitch)

> Hackathon UNASP + IBM 2026 — entrega às 19h.
> Resumo das correções aplicadas na manhã/tarde da entrega.
> Cada item lista **o que mudou**, **por quê** e **arquivo**, para defesa em arguição.

---

## 🔧 Frontend — URL da API parametrizada

**Arquivos:** `public/asset/js/api-config.js`, `public/asset/js/script-index.js`, `public/index.html`

**Antes:** `script-index.js` tinha `const NGROK_URL = "https://coveting-economy-tingling.ngrok-free.dev"` chumbado e o `api-config.js` enviava header `ngrok-skip-browser-warning`. O painel só funcionava com o túnel ngrok do dev original ligado.

**Depois:** resolução em camadas em `api-config.js`:

1. `localStorage["matchhelp_api"]` (override manual via DevTools)
2. `<meta name="matchhelp-api">` (futuro: injeção pelo backend)
3. `window.location.origin` (caso ideal — FastAPI servindo o HTML)
4. Fallback `http://192.241.151.209:8000` (a VPS de produção)

`script-index.js` agora consome `window.MATCHHELP_API` em vez de uma constante.

**Por quê:**
- Abrir o `index.html` direto no navegador (`file://`) ou servido por qualquer origem **passa a funcionar**.
- Em produção (FastAPI da VPS serve o HTML) a API resolve para a mesma origem — zero CORS extra.
- Header `ngrok-skip-browser-warning` removido por ser ruído desnecessário sem o túnel.
- O texto fixo no rodapé (`https://...ngrok-free.dev`) virou `detectando…` e é sobrescrito em runtime com a URL real.

---

## ⚡ Backend — query de login O(n) → O(log n)

**Arquivo:** `app/routers/auth.py`

**Antes:** o login carregava **todos os voluntários** em memória para comparar o `login_id` (8 primeiros chars do UUID). Custo proporcional ao tamanho da base.

```python
candidatos = db.execute(select(models.Voluntario)).scalars().all()
voluntario = next((v for v in candidatos if auth_svc.login_id_de(v.id).lower() == login_id), None)
```

**Depois:**

```python
if len(login_id) != auth_svc.LOGIN_ID_LEN or not all(c in "0123456789abcdef" for c in login_id):
    raise HTTPException(status_code=401, detail="Credenciais inválidas.")

stmt = (
    select(models.Voluntario)
    .where(cast(models.Voluntario.id, String).like(f"{login_id}%"))
    .limit(2)
)
candidatos = list(db.execute(stmt).scalars().all())
```

**Por quê:**
- **Validação de formato antes da query** — login_id mal formado nem chega ao banco e protege contra injeção em LIKE (whitelist hexadecimal).
- **`LIKE 'prefix%'` no UUID** usa o índice da PK (Postgres consegue usar o índice b-tree para prefix match após o cast). Mesmo no pior caso, é uma única query indexada em vez de table scan + materialização Python.
- **`.limit(2)`** detecta colisão (UUIDs com mesmo prefixo) sem trazer dezenas de linhas.
- O `next(...)` continua validando o `login_id_de(v.id)` exato — se houvesse colisão, ainda assim só passa o voluntário correto.

---

## 🛡️ Backend — justificativa de match nunca volta `null`

**Arquivo:** `app/routers/vinculos.py`

**Antes:** se `ia.justificar_match(ctx)` levantasse exceção (rede caindo, watsonx fora, payload mal formado), o frontend recebia `justificativa: null` e o card de match ficava sem o texto explicativo.

```python
try:
    justificativa = await ia.justificar_match(ctx)
except Exception:
    justificativa = None
```

**Depois — cadeia de fallback em três camadas:**

```python
justificativa: str | None = None
try:
    justificativa = await ia.justificar_match(ctx)
except Exception:
    try:
        justificativa = await _fallback_justificativa.justificar_match(ctx)
    except Exception:
        justificativa = (
            "Recomendado pelo algoritmo com base em skills, "
            "proximidade e reputação."
        )
```

`_fallback_justificativa` é um `IAFallbackKeywords` instanciado uma única vez no módulo (sem custo por requisição).

**Por quê:**
- A justificativa é **parte da UX** do painel — ela explica para a instituição **por que aquele voluntário foi sugerido**. Voltar `null` quebra a confiança da apresentação.
- O fallback de keywords é local (sem rede), então sobrevive a apagão do watsonx.
- A string fixa no terceiro nível garante que mesmo em catástrofe há texto.
- **Argumento de pitch:** "nosso pipeline de IA tem degradação graciosa em três níveis."

---

## 📚 Documentação

### `README.md`

- **Callout no topo** com URLs de produção (painel/Swagger/health da VPS).
- **Tabela de acesso comparativa** (local vs VPS).
- **Demo `curl` parametrizada** com `$API` em vez de `localhost` chumbado — uma única variável serve para rodar local ou contra a VPS.
- Dica explícita de override via `localStorage.setItem("matchhelp_api", ...)` para front local apontando para API VPS.

### `docs/PITCH_NOTES.md` (novo)

Cola completa para a apresentação:

- Pitch de 30s
- Tese central (3 fricções)
- Arquitetura em uma frase + diagrama
- Roteiro de demo passo-a-passo
- Algoritmo de matchmaking com tabela de pesos por urgência
- Por que IA aqui (e não regex)
- LGPD / privacidade
- Roadmap pós-hackathon
- 8 perguntas-zumbi com resposta pronta
- KPIs sugeridos
- Slogan de fechamento

### `docs/CHANGELOG_2026-04-27.md` (este arquivo)

Histórico das mudanças desta sprint final, para defesa em arguição.

---

## ✅ Como validar tudo de uma vez

Após o auto-deploy concluir (~30s pós-merge em `main`):

```bash
export API=http://192.241.151.209:8000

# 1. health
curl -fsS $API/health | jq .

# 2. seed + necessidade + match (verifica que justificativa nunca é null)
curl -X POST $API/api/v1/dev/seed-voluntarios-exemplo
NEC=$(curl -s -X POST $API/api/v1/necessidades \
  -H "Content-Type: application/json" \
  -d '{"descricao_crise":"Enchente, idosos sem atendimento médico","endereco":"São Paulo","latitude":-23.55,"longitude":-46.63}' \
  | jq -r '.resource_id')
sleep 2
curl -s -X POST $API/api/v1/vinculos \
  -H "Content-Type: application/json" \
  -d "{\"necessidade_id\":\"$NEC\",\"top_n\":3}" \
  | jq '.recomendacoes[] | {score: .score_match, dist: .distancia_km, just: .justificativa}'
```

`just` deve sempre vir preenchido — nunca `null`.

E o painel: abrir `http://192.241.151.209:8000/painel`, conferir que o footer mostra `ENDPOINT: http://192.241.151.209:8000` (e não `https://...ngrok-free.dev`).

---

## 🚀 Deploy

Tudo depende de push em `main`. O workflow `.github/workflows/deploy.yml` faz SSH na VPS, `git reset --hard origin/main`, `docker compose up -d --build` e bate `/health`. Health check OK → deploy ok.
