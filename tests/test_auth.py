import pytest
from fastapi import status


def test_login_sucesso(client):
    """Testa login com credenciais válidas e verificação de cookies."""
    response = client.post(
        "/login",
        data={"email": "admin@fellice.com.br", "senha": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == "/painel"
    assert "access_token" in response.cookies


def test_login_senha_incorreta(client):
    """Testa login com senha incorreta."""
    response = client.post(
        "/login",
        data={"email": "admin@fellice.com.br", "senha": "senhaErrada123"},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "E-mail ou senha incorretos" in response.text


def test_logout(client, admin_token):
    """Testa se o logout limpa os cookies e redireciona para login."""
    client.cookies.set("access_token", admin_token)
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == "/login"


def test_api_rest_login(client):
    """Testa endpoint JSON de autenticação REST para mobile/externos."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gerente.tatuape@fellice.com.br", "senha": "gerente123"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "GERENTE"
    assert data["user"]["loja_id"] is not None


def test_redirecionamento_usuario_deslogado(client):
    """Usuário sem cookie de sessão que acessa /painel no navegador é redirecionado para /login."""
    client.cookies.clear()
    response = client.get("/painel", follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/login"
