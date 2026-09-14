import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import criar_token
from app.database import Session
from app.models.usuario import Usuario


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_token():
    db = Session()
    try:
        user = db.query(Usuario).filter(Usuario.email == "admin@fellice.com.br").first()
        assert user is not None, "Usuário admin precisa estar semeado."
        token = criar_token({
            "sub": str(user.id),
            "email": user.email,
            "nome": user.nome,
            "role": user.role.value,
            "loja_id": user.loja_id,
        })
        return token
    finally:
        db.close()


@pytest.fixture
def gerente_token():
    db = Session()
    try:
        user = db.query(Usuario).filter(Usuario.email == "gerente.tatuape@fellice.com.br").first()
        assert user is not None, "Usuário gerente precisa estar semeado."
        token = criar_token({
            "sub": str(user.id),
            "email": user.email,
            "nome": user.nome,
            "role": user.role.value,
            "loja_id": user.loja_id,
        })
        return token
    finally:
        db.close()


@pytest.fixture
def funcionario_token():
    db = Session()
    try:
        user = db.query(Usuario).filter(Usuario.email == "funcionario.tatuape@fellice.com.br").first()
        assert user is not None, "Usuário funcionário precisa estar semeado."
        token = criar_token({
            "sub": str(user.id),
            "email": user.email,
            "nome": user.nome,
            "role": user.role.value,
            "loja_id": user.loja_id,
        })
        return token
    finally:
        db.close()
