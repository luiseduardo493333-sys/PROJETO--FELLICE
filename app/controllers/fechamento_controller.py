from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.fechamento import Fechamento, FechamentoItem, StatusFechamentoEnum, TurnoEnum
from app.models.loja import Loja
from app.models.usuario import RoleEnum
from app.auth import get_usuario_logado, get_gerente_ou_admin, validar_acesso_loja
from app.services.fechamento_service import (
    iniciar_fechamento,
    finalizar_fechamento,
    reabrir_fechamento,
)

router = APIRouter(prefix="/fechamentos", tags=["Fechamentos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_fechamentos(
    request: Request,
    loja_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Lista histórico de fechamentos de turno por loja."""
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

    query = db.query(Fechamento).options(
        joinedload(Fechamento.loja),
        joinedload(Fechamento.usuario),
        joinedload(Fechamento.reaberto_por),
    )
    if loja_alvo_id:
        query = query.filter(Fechamento.loja_id == loja_alvo_id)

    fechamentos = query.order_by(Fechamento.data_fechamento.desc()).limit(50).all()
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    turnos = [t.value for t in TurnoEnum]

    return templates.TemplateResponse(
        "fechamentos/index.html",
        {
            "request": request,
            "usuario": usuario,
            "fechamentos": fechamentos,
            "lojas": lojas,
            "loja_alvo_id": loja_alvo_id,
            "turnos": turnos,
        }
    )


@router.get("/novo", response_class=HTMLResponse)
def form_novo_fechamento(
    request: Request,
    loja_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Tela para abrir ou dar início ao fechamento de turno da filial."""
    if usuario.role == RoleEnum.ADMIN:
        cookie_loja = request.cookies.get("loja_ativa_id")
        if loja_id:
            loja_alvo_id = loja_id
        elif cookie_loja and cookie_loja.isdigit() and int(cookie_loja) > 0:
            loja_alvo_id = int(cookie_loja)
        else:
            primeira = db.query(Loja).filter(Loja.ativa == True).first()
            loja_alvo_id = primeira.id if primeira else 1
    else:
        loja_alvo_id = usuario.loja_id or 1

    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    loja_atual = db.query(Loja).filter(Loja.id == loja_alvo_id).first()

    return templates.TemplateResponse(
        "fechamentos/form.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "turnos": [t.value for t in TurnoEnum],
            "erro": None,
        }
    )


@router.post("/iniciar")
def executar_inicio_fechamento(
    request: Request,
    loja_id: int = Form(...),
    turno: str = Form("NOITE"),
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Inicia a sessão de fechamento de turno."""
    validar_acesso_loja(loja_id, usuario)
    turno_enum = TurnoEnum(turno)
    fechamento = iniciar_fechamento(db, loja_id=loja_id, usuario_id=usuario.id, turno=turno_enum)
    return RedirectResponse(url=f"/fechamentos/{fechamento.id}", status_code=status.HTTP_302_FOUND)


@router.post("/{fechamento_id}/finalizar")
def executar_finalizacao_fechamento(
    fechamento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Consolida os itens, congela o fechamento e bloqueia novas edições."""
    fechamento = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
    if not fechamento:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")
    validar_acesso_loja(fechamento.loja_id, usuario)

    finalizar_fechamento(db, fechamento_id=fechamento_id, usuario_id=usuario.id)
    return RedirectResponse(url=f"/fechamentos/{fechamento_id}", status_code=status.HTTP_302_FOUND)


@router.get("/{fechamento_id}", response_class=HTMLResponse)
def detalhes_fechamento(
    fechamento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Visualiza o fechamento com os itens congelados no momento do encerramento."""
    fechamento = (
        db.query(Fechamento)
        .options(
            joinedload(Fechamento.loja),
            joinedload(Fechamento.usuario),
            joinedload(Fechamento.reaberto_por),
            joinedload(Fechamento.itens).joinedload(FechamentoItem.produto),
        )
        .filter(Fechamento.id == fechamento_id)
        .first()
    )
    if not fechamento:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")
    validar_acesso_loja(fechamento.loja_id, usuario)

    total_diferenca_liquida = sum(item.diferenca for item in fechamento.itens)

    return templates.TemplateResponse(
        "fechamentos/detalhes.html",
        {
            "request": request,
            "usuario": usuario,
            "fechamento": fechamento,
            "total_diferenca_liquida": round(total_diferenca_liquida, 3),
        }
    )


@router.post("/{fechamento_id}/reabrir")
def executar_reabertura(
    fechamento_id: int,
    request: Request,
    justificativa: str = Form(...),
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Reabertura emergencial do fechamento mediante justificativa obrigatória."""
    fechamento = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
    if not fechamento:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado.")
    validar_acesso_loja(fechamento.loja_id, usuario)

    reabrir_fechamento(
        db, fechamento_id=fechamento_id, usuario_id=usuario.id, justificativa=justificativa
    )
    return RedirectResponse(url=f"/fechamentos/{fechamento_id}", status_code=status.HTTP_302_FOUND)
