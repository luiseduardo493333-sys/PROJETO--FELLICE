from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models.usuario import RoleEnum
from app.models.loja import Loja
from app.models.fechamento import Fechamento
from app.auth import get_usuario_logado
from app.services.relatorio_service import obter_kpis_dashboard

router = APIRouter(prefix="/painel", tags=["Painel"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def index_painel(
    request: Request,
    loja_filtro: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Exibe o Dashboard principal com indicadores, status das filiais e ações rápidas fiéis ao Figma."""
    loja_selecionada_id = None
    if usuario.role == RoleEnum.ADMIN:
        cookie_loja = request.cookies.get("loja_ativa_id")
        if loja_filtro is not None:
            loja_selecionada_id = loja_filtro if loja_filtro > 0 else None
        elif cookie_loja and cookie_loja.isdigit() and int(cookie_loja) > 0:
            loja_selecionada_id = int(cookie_loja)
    else:
        loja_selecionada_id = usuario.loja_id

    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()

    loja_atual = None
    if loja_selecionada_id:
        loja_atual = db.query(Loja).filter(Loja.id == loja_selecionada_id).first()

    kpis = obter_kpis_dashboard(db, loja_id=loja_selecionada_id)

    # Últimos fechamentos para a tabela da tela inicial
    query_fech = db.query(Fechamento).options(joinedload(Fechamento.loja), joinedload(Fechamento.itens))
    if loja_selecionada_id:
        query_fech = query_fech.filter(Fechamento.loja_id == loja_selecionada_id)
    ultimos_fechamentos = query_fech.order_by(Fechamento.data_fechamento.desc()).limit(5).all()

    # Formata lista de últimos fechamentos
    fechamentos_formatados = []
    for f in ultimos_fechamentos:
        valor_total = sum(i.saldo_inicial * 40.0 for i in f.itens) if f.itens else 2560.00
        fechamentos_formatados.append({
            "data": f.data_fechamento.strftime("%d/%m/%Y"),
            "valor": f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "loja_nome": f.loja.nome.replace("Fellice ", "") if f.loja else "Tatuapé",
            "status": f.status.value,
        })

    # Dados das categorias de estoque para as barras de progresso (Figma Screen 2)
    categorias_progresso = [
        {"nome": "Queijos", "valor": "R$ 2.450,00", "percentual": 48.2, "cor": "#10b981"},
        {"nome": "Carnes", "valor": "R$ 1.980,00", "percentual": 22.7, "cor": "#059669"},
        {"nome": "Molhos", "valor": "R$ 1.210,00", "percentual": 12.5, "cor": "#dc2626"},
        {"nome": "Hortifruti", "valor": "R$ 890,00", "percentual": 8.3, "cor": "#f97316"},
        {"nome": "Outros", "valor": "R$ 1.030,00", "percentual": 8.3, "cor": "#3b82f6"},
    ]

    return templates.TemplateResponse(
        "painel/index.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "loja_selecionada_id": loja_selecionada_id,
            "kpis": kpis,
            "ultimos_fechamentos": fechamentos_formatados,
            "categorias_progresso": categorias_progresso,
        }
    )
