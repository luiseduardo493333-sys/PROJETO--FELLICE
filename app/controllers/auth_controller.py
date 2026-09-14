from fastapi import APIRouter, Depends, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.auth import verificar_senha, criar_token, get_usuario_opcional

router = APIRouter(tags=["Autenticação"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request, usuario=Depends(get_usuario_opcional)):
    """Exibe tela de login se o usuário não estiver autenticado."""
    if usuario:
        return RedirectResponse(url="/painel", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/login.html", {"request": request, "erro": None})


@router.post("/login", response_class=HTMLResponse)
def executar_login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processa autenticação e grava cookie seguro com JWT."""
    usuario = db.query(Usuario).filter(Usuario.email == email.strip().lower()).first()

    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "erro": "E-mail ou senha incorretos.", "email": email},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not usuario.ativo:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "erro": "Usuário inativo no sistema.", "email": email},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Gera token JWT
    token_jwt = criar_token({
        "sub": str(usuario.id),
        "email": usuario.email,
        "nome": usuario.nome,
        "role": usuario.role.value,
        "loja_id": usuario.loja_id,
    })

    resposta = RedirectResponse(url="/painel", status_code=status.HTTP_302_FOUND)
    # Define cookie de acesso
    resposta.set_cookie(
        key="access_token",
        value=token_jwt,
        httponly=True,
        max_age=60 * 60 * 8, # 8 horas
        samesite="lax",
    )
    # Se usuário tiver loja vinculada, define cookie de loja ativa
    if usuario.loja_id:
        resposta.set_cookie(key="loja_ativa_id", value=str(usuario.loja_id), samesite="lax")

    return resposta


@router.get("/logout")
def executar_logout():
    """Limpa cookies de autenticação e redireciona para tela de login."""
    resposta = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    resposta.delete_cookie(key="access_token")
    resposta.delete_cookie(key="loja_ativa_id")
    return resposta
