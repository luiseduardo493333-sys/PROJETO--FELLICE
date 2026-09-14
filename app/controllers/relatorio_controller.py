from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.loja import Loja
from app.models.usuario import RoleEnum
from app.auth import get_usuario_logado, get_admin
from app.services.relatorio_service import (
    obter_relatorio_semanal,
    obter_relatorio_divergencias,
    obter_comparativo_lojas,
)

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def index_relatorios(
    request: Request,
    loja_id: Optional[int] = None,
    dias: int = 7,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Exibe relatórios de movimentação semanal e ranking de divergências."""
    if usuario.role == RoleEnum.ADMIN:
        cookie_loja = request.cookies.get("loja_ativa_id")
        if loja_id:
            loja_alvo_id = loja_id
        elif cookie_loja and cookie_loja.isdigit() and int(cookie_loja) > 0:
            loja_alvo_id = int(cookie_loja)
        else:
            loja_alvo_id = None
    else:
        loja_alvo_id = usuario.loja_id

    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    loja_atual = db.query(Loja).filter(Loja.id == loja_alvo_id).first() if loja_alvo_id else None

    relatorio_semanal = obter_relatorio_semanal(db, loja_id=loja_alvo_id)
    relatorio_divergencias = obter_relatorio_divergencias(db, loja_id=loja_alvo_id, dias=dias)

    return templates.TemplateResponse(
        "relatorios/index.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "loja_alvo_id": loja_alvo_id,
            "dias": dias,
            "relatorio_semanal": relatorio_semanal,
            "relatorio_divergencias": relatorio_divergencias,
        }
    )


@router.get("/comparativo", response_class=HTMLResponse)
def relatorio_comparativo(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Visão exclusiva do Administrador comparando o desempenho entre filiais."""
    comparativo = obter_comparativo_lojas(db)

    return templates.TemplateResponse(
        "relatorios/comparativo.html",
        {
            "request": request,
            "usuario": usuario,
            "comparativo": comparativo,
        }
    )
