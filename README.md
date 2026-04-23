# 🚨 Voluntariado Inteligente para Crises

> **Hackathon UNASP 2026** — _Orquestrando o Voluntariado Inteligente para Situações de Crise_

API de orquestração que conecta **instituições em situação de crise** com **voluntários qualificados**, utilizando correspondência baseada em habilidades (_skill-based volunteering_). Projetada para integração com o **IBM watsonx Orchestrate** como Skill.

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Arquitetura](#-arquitetura)
- [Stack Tecnológica](#-stack-tecnológica)
- [Pré-requisitos](#-pré-requisitos)
- [Como Rodar](#-como-rodar)
- [Endpoints da API](#-endpoints-da-api)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Padrão de Commits](#-padrão-de-commits)

---

## 💡 Sobre o Projeto

Em situações de crise — enchentes, deslizamentos, incêndios — cada minuto conta. Este sistema permite que instituições descrevam a emergência e as habilidades necessárias, e a API automaticamente encontra e retorna voluntários compatíveis, priorizados por proximidade geográfica.

### Fluxo principal

```
Instituição → descreve a crise → API orquestra → retorna voluntários compatíveis
```

1. A instituição envia uma **necessidade emergencial** (descrição, habilidades, localização, urgência).
2. A API realiza a **correspondência de habilidades** com voluntários cadastrados.
3. Retorna uma lista de **voluntários compatíveis** ordenados por proximidade.

---

## 🏗 Arquitetura

```
┌─────────────────────┐       ┌──────────────────┐       ┌──────────────┐
│  IBM watsonx         │       │                  │       │              │
│  Orchestrate         │──────▶│   FastAPI (API)   │──────▶│  PostgreSQL  │
│  (Consumidor Skill)  │       │   :8000           │       │  :5432       │
└─────────────────────┘       └──────────────────┘       └──────────────┘
```

A API expõe um contrato **OpenAPI/Swagger** rico em descrições para que o watsonx Orchestrate consiga interpretar e utilizar as rotas automaticamente como Skills.

---

## 🛠 Stack Tecnológica

| Tecnologia       | Versão   | Função                          |
|------------------|----------|---------------------------------|
| Python           | 3.11     | Linguagem principal             |
| FastAPI          | 0.111.0  | Framework web assíncrono        |
| Uvicorn          | 0.30.1   | Servidor ASGI                   |
| Pydantic         | 2.7.4    | Validação e schemas de dados    |
| SQLAlchemy       | 2.0.31   | ORM para banco de dados         |
| Psycopg2         | 2.9.9    | Driver PostgreSQL               |
| PostgreSQL       | 15       | Banco de dados relacional       |
| Docker + Compose | —        | Containerização e orquestração  |

---

## ✅ Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- [Git](https://git-scm.com/)

> **Nota:** Não é necessário instalar Python ou PostgreSQL localmente — tudo roda via Docker.

---

## 🚀 Como Rodar

### 1. Clone o repositório

```bash
git clone https://github.com/TeuszMAN/hackaton-unasp-2026.git
cd hackaton-unasp-2026
```

### 2. Suba os containers

```bash
docker compose up --build
```

### 3. Acesse a API

| Recurso                  | URL                                        |
|--------------------------|--------------------------------------------|
| Health Check             | http://localhost:8000/                      |
| Swagger UI (Documentação)| http://localhost:8000/docs                  |
| ReDoc                    | http://localhost:8000/redoc                 |
| OpenAPI JSON             | http://localhost:8000/openapi.json          |

### 4. Teste a rota principal

```bash
curl -X POST http://localhost:8000/api/v1/orquestrar-resgate \
  -H "Content-Type: application/json" \
  -d '{
    "descricao_crise": "Enchente atingiu abrigo comunitário no bairro Vila Nova",
    "habilidades_requeridas": ["primeiros_socorros", "resgate_aquatico"],
    "localizacao": "Rua das Flores, 123 - Vila Nova, São Paulo - SP",
    "nivel_urgencia": "critico"
  }'
```

---

## 📡 Endpoints da API

### `GET /` — Health Check

Verifica se a API está online e operacional.

**Resposta:**
```json
{
  "status": "ok",
  "service": "voluntariado-inteligente-api",
  "version": "0.1.0"
}
```

---

### `POST /api/v1/orquestrar-resgate` — Orquestrar Resgate

Recebe uma necessidade emergencial e retorna voluntários compatíveis.

**Request Body:**

| Campo                   | Tipo       | Obrigatório | Descrição                                            |
|-------------------------|------------|-------------|------------------------------------------------------|
| `descricao_crise`       | `string`   | ✅          | Descrição detalhada da situação de crise              |
| `habilidades_requeridas`| `string[]` | ✅          | Lista de habilidades necessárias                      |
| `localizacao`           | `string`   | ✅          | Endereço ou coordenadas do local da crise             |
| `nivel_urgencia`        | `enum`     | ✅          | `baixo`, `medio`, `alto` ou `critico`                 |

**Response Body:**

| Campo                | Tipo               | Descrição                                   |
|----------------------|--------------------|---------------------------------------------|
| `total_voluntarios`  | `int`              | Quantidade de voluntários encontrados        |
| `voluntarios`        | `VoluntarioMatch[]`| Lista de voluntários ordenados por distância |

Cada `VoluntarioMatch` contém:

| Campo                      | Tipo     | Descrição                                  |
|----------------------------|----------|--------------------------------------------|
| `nome`                     | `string` | Nome completo do voluntário                |
| `telefone`                 | `string` | Telefone com DDD                           |
| `habilidade_correspondente`| `string` | Habilidade que motivou a seleção           |
| `distancia_km`             | `float`  | Distância em km até o local da crise       |

> ⚠️ **Nota:** Atualmente a rota retorna dados mockados para validação do contrato OpenAPI.

---

## 📁 Estrutura do Projeto

```
hackaton-unasp-2026/
├── main.py              # Aplicação FastAPI (schemas + rotas)
├── requirements.txt     # Dependências Python
├── Dockerfile           # Imagem Docker da API
├── docker-compose.yml   # Orquestração dos serviços (API + DB)
├── .gitignore           # Arquivos ignorados pelo Git
└── README.md            # Este arquivo
```

---

## 📝 Padrão de Commits

Trabalhamos com o padrão **[Conventional Commits](https://www.conventionalcommits.org/)**. Ao abrir um PR ou fazer um commit direto, utilize os prefixos:

| Prefixo  | Uso                               |
|----------|------------------------------------|
| `feat:`  | Novas features                     |
| `fix:`   | Correções de bugs                  |
| `chore:` | Atualizações de infra/dependências |
| `docs:`  | Documentação                       |

**Exemplo:**
```
feat: adiciona rota de orquestração de resgate
```

---

## 👥 Equipe

Gabriel Yoshino
Lais Gonçalves
Mateus Alves
Vitor Bueno

