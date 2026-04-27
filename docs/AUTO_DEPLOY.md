# Auto-deploy via GitHub Actions

Workflow: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).

A cada `push` no branch `main` (ou disparo manual em **Actions → Deploy to VPS → Run workflow**), o workflow conecta na VPS via SSH e executa:

```bash
cd /root/hackaton-unasp-2026
git fetch --prune origin
git checkout main
git reset --hard origin/main
docker compose up -d --build --remove-orphans
docker image prune -f
curl --fail http://localhost:8000/health
```

> **`git reset --hard origin/main`** descarta qualquer alteração local não commitada no diretório da VPS. Isso é proposital — garante que a VPS sempre reflete o `main` do GitHub. Se você precisar editar arquivos diretamente na VPS para teste, faça em outro diretório.

---

## 1. Secrets a configurar no GitHub

Vá em **Settings → Secrets and variables → Actions → New repository secret** e crie:

| Secret | Valor | Obrigatório |
|---|---|---|
| `VPS_HOST` | `192.241.151.209` | sim |
| `VPS_USER` | `root` | sim |
| `VPS_PASSWORD` | senha do `root` | sim |
| `VPS_PORT` | porta SSH (default `22`) | só se for diferente |

---

## 2. Pré-requisitos na VPS

Confira **uma única vez**:

```bash
# 1. O diretório existe e é um repo git apontando para o repo certo
cd /root/hackaton-unasp-2026
git remote -v
# origin  git@github.com:TeuszMAN/hackaton-unasp-2026.git (fetch)
# origin  git@github.com:TeuszMAN/hackaton-unasp-2026.git (push)

# 2. O usuário consegue rodar docker sem sudo
docker ps

# 3. docker compose v2 está disponível
docker compose version

# 4. SSH com senha está habilitado (sshd_config)
grep -E "^PasswordAuthentication" /etc/ssh/sshd_config
# Esperado: PasswordAuthentication yes
```

Se o `git remote` estiver via SSH (`git@github.com:...`) e a porta 22 estiver bloqueada para sair da VPS, troque para HTTPS para o `git pull` funcionar:

```bash
git remote set-url origin https://github.com/TeuszMAN/hackaton-unasp-2026.git
```

(Repo público, então não precisa de credencial.)

---

## 3. Como testar

1. Configurar os secrets acima.
2. Commit + push qualquer alteração no `main` (ou abrir **Actions → Deploy to VPS → Run workflow**).
3. Acompanhar a execução em **Actions**. Os logs mostram `git pull`, `docker compose build` e o health check.
4. Validar que a API respondeu: `curl http://192.241.151.209:8000/health`.

---

## 4. Recomendações de segurança (próximos passos)

- **Trocar senha por chave SSH.** Auth com senha + `root` direto deixa a VPS exposta a brute-force. Crie um usuário `deploy`, suba sua chave pública (`ssh-copy-id`), troque o secret `VPS_PASSWORD` por `VPS_SSH_KEY` e ajuste o `with:` do workflow para `key: ${{ secrets.VPS_SSH_KEY }}`.
- **Fail2ban** na VPS para limitar brute-force enquanto a senha estiver ativa.
- **Limitar SSH ao IP do GitHub Actions** não é viável (pool grande e dinâmico). A camada certa é desativar password auth assim que possível.
- **Logs estruturados** — o Actions só mostra exit code; para investigar falhas em runtime, use `docker compose logs -f` na VPS ou exporte para um agregador.

---

## 5. Troubleshooting

| Sintoma | Causa provável | Resolução |
|---|---|---|
| `Permission denied (publickey,password)` | Senha errada ou `PasswordAuthentication no` | Verificar secret e `sshd_config`, `systemctl reload ssh` |
| `git pull` fala em `host key verification failed` | known_hosts vazio na VPS | Rodar uma vez `ssh -T git@github.com` (ou usar HTTPS no remote) |
| `docker: command not found` | PATH do shell não interativo | Usar `script:` com path absoluto: `/usr/bin/docker` |
| Health check falha com 5xx | Container subiu mas API morreu | `docker compose logs --tail=200` na VPS |
| Workflow trava em "Deploy via SSH" | Firewall bloqueando 22 saída do GitHub | Usar runner self-hosted na VPS, ou webhook |
