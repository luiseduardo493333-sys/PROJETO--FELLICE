"""
Módulo de Autenticação e Controle de Acesso Baseado em Perfis (RBAC).
Utiliza as rotinas de segurança centralizadas em app.core.security.
"""
from typing import Optional
from jose import JWTError
from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    hash_senha,
    verificar_senha,
    criar_token,
    decodificar_token,
)
from app.core.database import get_db

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def get_token_from_request(request: Request) -> Optional[str]:
    """Extrai o token JWT do cabeçalho Authorization Bearer ou dos cookies."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1].strip()
    return request.cookies.get("access_token")


def get_usuario_logado(request: Request, db: Session = Depends(get_db)):
    """
    Retorna o objeto do usuário autenticado no banco de dados.
    Caso não esteja logado, redireciona para login ou lança 401.
    """
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Faça login para continuar."
        )

    try:
        payload = decodificar_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido."
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado ou inválido."
        )

    # Import local para evitar import cíclico
    from app.models.usuario import Usuario
    usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo ou não encontrado."
        )

    return usuario


def get_usuario_opcional(request: Request, db: Session = Depends(get_db)):
    """Retorna usuário logado se existir token válido, ou None caso contrário."""
    token = get_token_from_request(request)
    if not token:
        return None
    try:
        payload = decodificar_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        from app.models.usuario import Usuario
        return db.query(Usuario).filter(Usuario.id == int(user_id), Usuario.ativo == True).first()
    except Exception:
        return None


def get_admin(usuario=Depends(get_usuario_logado)):
    """Garante que o usuário logado possui perfil de ADMINISTRADOR."""
    from app.models.usuario import RoleEnum
    if usuario.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Administrador Geral."
        )
    return usuario


def get_gerente_ou_admin(usuario=Depends(get_usuario_logado)):
    """Garante que o usuário possui perfil GERENTE ou ADMIN."""
    from app.models.usuario import RoleEnum
    if usuario.role not in [RoleEnum.ADMIN, RoleEnum.GERENTE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a Gerentes e Administradores."
        )
    return usuario


def validar_acesso_loja(loja_id: int, usuario) -> None:
    """
    Garante o isolamento multi-loja (RN01):
    - ADMIN pode acessar qualquer loja.
    - GERENTE e FUNCIONARIO só podem acessar sua própria filial.
    """
    from app.models.usuario import RoleEnum
    if usuario.role == RoleEnum.ADMIN:
        return

    if usuario.loja_id != loja_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: Você não possui permissão para acessar a loja {loja_id}."
        )
