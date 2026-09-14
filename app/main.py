import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.database import engine, Base
import app.models  # Garante que todos os modelos sejam importados e mapeados

from app.controllers import (
    auth_controller,
    painel_controller,
    loja_controller,
    produto_controller,
    estoque_controller,
    entrada_controller,
    contagem_controller,
    fechamento_controller,
    relatorio_controller,
    usuario_controller,
    auditoria_controller,
    api_controller,
)

load_dotenv()

# Criação automática de tabelas do banco de dados relacional
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pizzaria Fellice - Controle Operacional e de Estoque",
    description="Sistema multi-lojas de gestão de estoque, contagens diárias, fechamento de turnos e auditoria para a Pizzaria Fellice (Tatuapé, Aricanduva, Nhocuné).",
    version="1.0.0",
)

# Montagem de arquivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Tratamento global de exceções HTTP
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Se o usuário não está autenticado (401)
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Se for requisição para a API REST (mobile ou externa), responde em JSON
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        # Se for acesso web via navegador, redireciona suavemente para a tela de login
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Demais códigos de status HTTP (400, 403, 404, etc.)
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Registro dos roteadores MVC e da API REST
app.include_router(auth_controller.router)
app.include_router(painel_controller.router)
app.include_router(loja_controller.router)
app.include_router(produto_controller.router)
app.include_router(estoque_controller.router)
app.include_router(entrada_controller.router)
app.include_router(contagem_controller.router)
app.include_router(fechamento_controller.router)
app.include_router(relatorio_controller.router)
app.include_router(usuario_controller.router)
app.include_router(auditoria_controller.router)
app.include_router(api_controller.router)


@app.get("/")
def raiz(request: Request):
    """Página inicial: redireciona para o Painel Geral se logado, ou Login se anônimo."""
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/painel")
    return RedirectResponse(url="/login")
