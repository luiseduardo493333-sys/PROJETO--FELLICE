from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.loja import Loja
from app.models.usuario import RoleEnum
from app.auth import get_usuario_logado
from app.services.estoque_service import obter_estoque_loja

router = APIRouter(prefix="/estoque", tags=["Estoque"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def consultar_estoque(
    request: Request,
    loja_id: Optional[int] = None,
    filtro_status: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Exibe posição de estoque atual em tempo real da loja."""
    # Define a loja a ser consultada
    if usuario.role == RoleEnum.ADMIN:
        cookie_loja = request.cookies.get("loja_ativa_id")
        if loja_id:
            loja_alvo_id = loja_id
        elif cookie_loja and cookie_loja.isdigit() and int(cookie_loja) > 0:
            loja_alvo_id = int(cookie_loja)
        else:
            primeira_loja = db.query(Loja).filter(Loja.ativa == True).first()
            loja_alvo_id = primeira_loja.id if primeira_loja else 1
    else:
        loja_alvo_id = usuario.loja_id or 1

    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    loja_atual = db.query(Loja).filter(Loja.id == loja_alvo_id).first()

    itens_estoque = obter_estoque_loja(db, loja_id=loja_alvo_id)

    if filtro_status == "critico":
        itens_estoque = [i for i in itens_estoque if i["status_estoque"] == "CRITICO"]
    elif filtro_status == "baixo":
        itens_estoque = [i for i in itens_estoque if i["status_estoque"] in ["BAIXO", "CRITICO"]]

    total_itens = len(itens_estoque)
    itens_alerta = sum(1 for i in itens_estoque if i["alerta_reposicao"])

    return templates.TemplateResponse(
        "estoque/index.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "itens_estoque": itens_estoque,
            "total_itens": total_itens,
            "itens_alerta": itens_alerta,
            "filtro_status": filtro_status,
        }
    )
