"""
Router — Autenticação de voluntário.

Fluxo:
  1. `POST /api/v1/voluntarios` cria o voluntário e gera senha temporária
     (válida por 2h). O agente exibe a senha ao usuário no chat.
  2. `POST /api/v1/auth/login` autentica com login_id (8 chars) + senha.
     Aceita tanto a senha temporária (enquanto válida) quanto a senha
     definitiva.
  3. Se `precisa_trocar_senha=True`, o frontend redireciona para a tela
     de troca antes de qualquer outra ação.
  4. `POST /api/v1/auth/trocar-senha` (autenticado) define a senha
     definitiva e zera os campos temporários.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import auth as auth_svc


router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=schemas.LoginResponse,
    summary="Login de voluntário (login_id + senha)",
    description=(
        "Autentica um voluntário usando os 8 primeiros caracteres do seu "
        "voluntario_id e a senha (temporária ou definitiva). Retorna um token "
        "de sessão a ser enviado em `Authorization: Bearer <token>` nas "
        "próximas chamadas."
    ),
)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    login_id = payload.login_id.lower().strip()

    # Sanity check: login_id é o prefixo hexadecimal do UUID (8 chars).
    # Validar antes de consultar o banco evita query desnecessária e
    # protege contra injeção em LIKE.
    if len(login_id) != auth_svc.LOGIN_ID_LEN or not all(
        c in "0123456789abcdef" for c in login_id
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    # Filtra direto no banco usando o prefixo do UUID — O(log n) com índice
    # vs O(n) carregando a tabela inteira em memória.
    stmt = (
        select(models.Voluntario)
        .where(cast(models.Voluntario.id, String).like(f"{login_id}%"))
        .limit(2)
    )
    candidatos = list(db.execute(stmt).scalars().all())

    voluntario = next(
        (v for v in candidatos if auth_svc.login_id_de(v.id).lower() == login_id),
        None,
    )
    if voluntario is None:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    agora = datetime.now(timezone.utc)

    senha_ok = False
    if voluntario.senha_hash and auth_svc.verificar_senha(payload.senha, voluntario.senha_hash):
        senha_ok = True
    elif (
        voluntario.senha_temp_hash
        and voluntario.senha_temp_expira_em is not None
    ):
        expira = voluntario.senha_temp_expira_em
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if expira > agora and auth_svc.verificar_senha(
            payload.senha, voluntario.senha_temp_hash
        ):
            senha_ok = True

    if not senha_ok:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    sessao = auth_svc.criar_sessao(voluntario.id)
    return schemas.LoginResponse(
        token=sessao.token,
        voluntario_id=voluntario.id,
        nome=voluntario.nome,
        precisa_trocar_senha=voluntario.precisa_trocar_senha,
        expira_em=sessao.expira_em,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/trocar-senha
# ---------------------------------------------------------------------------
@router.post(
    "/trocar-senha",
    response_model=schemas.LoginResponse,
    summary="Trocar a senha do voluntário autenticado",
    description=(
        "Exige header `Authorization: Bearer <token>`. Verifica a senha atual "
        "(temporária ou definitiva) e grava a nova senha em hash. Limpa os "
        "campos de senha temporária e zera `precisa_trocar_senha`. Retorna um "
        "novo token de sessão (rotaciona)."
    ),
)
def trocar_senha(
    payload: schemas.TrocarSenhaRequest,
    voluntario_id=Depends(auth_svc.voluntario_autenticado),
    db: Session = Depends(get_db),
):
    voluntario = db.get(models.Voluntario, voluntario_id)
    if voluntario is None:
        raise HTTPException(status_code=404, detail="Voluntário não encontrado.")

    agora = datetime.now(timezone.utc)
    senha_ok = False
    if voluntario.senha_hash and auth_svc.verificar_senha(
        payload.senha_atual, voluntario.senha_hash
    ):
        senha_ok = True
    elif (
        voluntario.senha_temp_hash
        and voluntario.senha_temp_expira_em is not None
    ):
        expira = voluntario.senha_temp_expira_em
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if expira > agora and auth_svc.verificar_senha(
            payload.senha_atual, voluntario.senha_temp_hash
        ):
            senha_ok = True

    if not senha_ok:
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")

    if payload.nova_senha == payload.senha_atual:
        raise HTTPException(
            status_code=400,
            detail="A nova senha precisa ser diferente da senha atual.",
        )

    voluntario.senha_hash = auth_svc.hash_senha(payload.nova_senha)
    voluntario.senha_temp_hash = None
    voluntario.senha_temp_expira_em = None
    voluntario.precisa_trocar_senha = False
    db.commit()
    db.refresh(voluntario)

    sessao = auth_svc.criar_sessao(voluntario.id)
    return schemas.LoginResponse(
        token=sessao.token,
        voluntario_id=voluntario.id,
        nome=voluntario.nome,
        precisa_trocar_senha=voluntario.precisa_trocar_senha,
        expira_em=sessao.expira_em,
    )
