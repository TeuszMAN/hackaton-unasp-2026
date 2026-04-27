"""
Serviço de autenticação de voluntário.

Implementação simples para o escopo do hackathon:
  - Senhas armazenadas em bcrypt (passlib).
  - Tokens de sessão opacos, gerados aleatoriamente, mantidos em memória.
  - Senha temporária válida por 2 horas após o cadastro.

Em produção: trocar o store em memória por Redis / tabela `Sessao`, e usar
JWT assinado se for necessário escalar horizontalmente.
"""

from __future__ import annotations

import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from passlib.context import CryptContext


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
SENHA_TEMP_VALIDADE_HORAS = 2.0
SESSAO_VALIDADE_HORAS = 12.0
LOGIN_ID_LEN = 8

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Geração de senha temporária
# ---------------------------------------------------------------------------
def gerar_senha_temporaria(tamanho: int = 8) -> str:
    """
    Gera uma senha temporária amigável: maiúsculas + dígitos, sem caracteres
    ambíguos (0/O, 1/I/l). Ex.: 'X9T2PQR4'.
    """
    alfabeto = "".join(c for c in (string.ascii_uppercase + string.digits) if c not in "O0I1L")
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def calcular_expiracao_temp() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=SENHA_TEMP_VALIDADE_HORAS)


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def hash_senha(senha: str) -> str:
    return _pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    if not senha_hash:
        return False
    try:
        return _pwd_context.verify(senha, senha_hash)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Login ID a partir do UUID
# ---------------------------------------------------------------------------
def login_id_de(voluntario_id: uuid.UUID) -> str:
    return str(voluntario_id).replace("-", "")[:LOGIN_ID_LEN]


# ---------------------------------------------------------------------------
# Sessões em memória
# ---------------------------------------------------------------------------
@dataclass
class Sessao:
    token: str
    voluntario_id: uuid.UUID
    expira_em: datetime


_SESSOES: dict[str, Sessao] = {}


def criar_sessao(voluntario_id: uuid.UUID) -> Sessao:
    token = secrets.token_urlsafe(32)
    expira_em = datetime.now(timezone.utc) + timedelta(hours=SESSAO_VALIDADE_HORAS)
    sessao = Sessao(token=token, voluntario_id=voluntario_id, expira_em=expira_em)
    _SESSOES[token] = sessao
    return sessao


def obter_sessao(token: str) -> Sessao | None:
    sessao = _SESSOES.get(token)
    if sessao is None:
        return None
    if sessao.expira_em <= datetime.now(timezone.utc):
        _SESSOES.pop(token, None)
        return None
    return sessao


def invalidar_sessao(token: str) -> None:
    _SESSOES.pop(token, None)


# ---------------------------------------------------------------------------
# Dependência FastAPI: autenticação obrigatória
# ---------------------------------------------------------------------------
def voluntario_autenticado(authorization: str | None = Header(None)) -> uuid.UUID:
    """
    Lê o header `Authorization: Bearer <token>` e retorna o `voluntario_id`
    correspondente. Levanta 401 se ausente, malformado ou expirado.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token de sessão ausente.")
    token = authorization.split(None, 1)[1].strip()
    sessao = obter_sessao(token)
    if sessao is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return sessao.voluntario_id
