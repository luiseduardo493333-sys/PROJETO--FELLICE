from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.loja import Loja
from app.models.usuario import RoleEnum, Usuario
from app.models.estoque import LojaProduto
from app.auth import get_usuario_logado, get_admin
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/lojas", tags=["Lojas"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_lojas(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Lista as filiais da pizzaria."""
    if usuario.role == RoleEnum.ADMIN:
        lojas = db.query(Loja).order_by(Loja.nome).all()
    else:
        lojas = db.query(Loja).filter(Loja.id == usuario.loja_id).all()

    # Contagem de funcionários e produtos por loja
    dados_lojas = []
    for loja in lojas:
        total_funcionarios = db.query(func.count(Usuario.id)).filter(Usuario.loja_id == loja.id, Usuario.ativo == True).scalar() or 0
        total_produtos = db.query(func.count(LojaProduto.id)).filter(LojaProduto.loja_id == loja.id, LojaProduto.ativo == True).scalar() or 0
        dados_lojas.append({
            "loja": loja,
            "total_funcionarios": total_funcionarios,
            "total_produtos": total_produtos,
        })

    cookie_loja = request.cookies.get("loja_ativa_id")
    loja_ativa_id = int(cookie_loja) if cookie_loja and cookie_loja.isdigit() else (usuario.loja_id or 0)

    return templates.TemplateResponse(
        "lojas/index.html",
        {
            "request": request,
            "usuario": usuario,
            "dados_lojas": dados_lojas,
            "loja_ativa_id": loja_ativa_id,
        }
    )


@router.get("/novo", response_class=HTMLResponse)
def form_nova_loja(
    request: Request,
    usuario = Depends(get_admin),
):
    """Formulário para cadastrar nova filial (apenas Admin)."""
    return templates.TemplateResponse(
        "lojas/form.html",
        {"request": request, "usuario": usuario, "loja": None, "erro": None}
    )


@router.post("/novo", response_class=HTMLResponse)
def salvar_nova_loja(
    request: Request,
    nome: str = Form(...),
    codigo: str = Form(...),
    endereco: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Cria nova filial no banco de dados."""
    nome_limpo = nome.strip()
    codigo_limpo = codigo.strip().upper()

    existente = db.query(Loja).filter((Loja.nome == nome_limpo) | (Loja.codigo == codigo_limpo)).first()
    if existente:
        return templates.TemplateResponse(
            "lojas/form.html",
            {
                "request": request,
                "usuario": usuario,
                "loja": None,
                "erro": "Já existe uma loja cadastrada com este nome ou código identificador.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    nova_loja = Loja(
        nome=nome_limpo,
        codigo=codigo_limpo,
        endereco=endereco.strip() if endereco else None,
        telefone=telefone.strip() if telefone else None,
        ativa=True,
    )
    db.add(nova_loja)
    db.commit()
    db.refresh(nova_loja)

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=nova_loja.id,
        entidade="LOJA",
        entidade_id=nova_loja.id,
        acao="CRIACAO",
        dados_novos={"nome": nova_loja.nome, "codigo": nova_loja.codigo},
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/lojas", status_code=status.HTTP_302_FOUND)


@router.post("/{loja_id}/selecionar")
def selecionar_loja_ativa(
    loja_id: int,
    request: Request,
    usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """Permite ao Administrador alternar a loja ativa no contexto de navegação."""
    if usuario.role != RoleEnum.ADMIN and usuario.loja_id != loja_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")

    resposta = RedirectResponse(url=request.headers.get("referer", "/painel"), status_code=status.HTTP_302_FOUND)
    resposta.set_cookie(key="loja_ativa_id", value=str(loja_id), samesite="lax")
    return resposta
