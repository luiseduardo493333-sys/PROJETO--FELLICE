from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.usuario import Usuario, RoleEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo no sistema",
        )
    return user


class RoleChecker:
    """Valida se o usuário autenticado possui algum dos papéis permitidos."""
    def __init__(self, allowed_roles: List[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão negada. Apenas perfis {[r.value for r in self.allowed_roles]} têm acesso a esta operação.",
            )
        return current_user


# Helpers de injeção de papel
allow_admin = RoleChecker([RoleEnum.ADMIN])
allow_gerente_or_admin = RoleChecker([RoleEnum.ADMIN, RoleEnum.GERENTE])
allow_all_authenticated = RoleChecker([RoleEnum.ADMIN, RoleEnum.GERENTE, RoleEnum.FUNCIONARIO])


def verify_loja_access(loja_id: int, current_user: Usuario) -> None:
    """
    Garante o isolamento multi-loja (RN01):
    - ADMIN pode acessar qualquer loja.
    - GERENTE e FUNCIONARIO só podem acessar a filial vinculada em seu cadastro.
    """
    if current_user.role == RoleEnum.ADMIN:
        return

    if current_user.loja_id != loja_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: Você não tem permissão para visualizar ou alterar dados da loja {loja_id}.",
        )
