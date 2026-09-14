from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.audit import AuditLog
from app.auth import get_admin

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_auditoria(
    request: Request,
    entidade: Optional[str] = None,
    acao: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Consulta os registros de auditoria e rastreabilidade (apenas Administrador)."""
    query = db.query(AuditLog).options(joinedload(AuditLog.usuario))

    if entidade:
        query = query.filter(AuditLog.entidade == entidade.upper())
    if acao:
        query = query.filter(AuditLog.acao == acao.upper())

    logs = query.order_by(AuditLog.created_at.desc()).limit(100).all()

    return templates.TemplateResponse(
        "auditoria/index.html",
        {
            "request": request,
            "usuario": usuario,
            "logs": logs,
            "entidade_filtro": entidade,
            "acao_filtro": acao,
        }
    )
