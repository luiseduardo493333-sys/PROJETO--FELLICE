from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import json

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.loja import Loja
from app.models.audit import AuditLog
from app.auth import get_admin, hash_senha
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Lista usuários cadastrados e histórico de transferências (Figma Screen 8 e 9)."""
    usuarios = db.query(Usuario).options(joinedload(Usuario.loja)).order_by(Usuario.nome).all()
    lojas = db.query(Loja).filter(Loja.ativa == True).all()

    # Busca histórico de transferências dos logs de auditoria
    logs_transf = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.usuario))
        .filter(AuditLog.entidade == "USUARIO", AuditLog.acao == "TRANSFERENCIA_LOJA")
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    historico_transferencias = []
    for log in logs_transf:
        try:
            dados = json.loads(log.dados_novos) if log.dados_novos else {}
            historico_transferencias.append({
                "usuario_nome": dados.get("usuario_nome", "Usuário"),
                "de": dados.get("loja_anterior", "-"),
                "para": dados.get("loja_nova", "-"),
                "data": log.created_at.strftime("%d/%m/%Y"),
            })
        except Exception:
            pass

    # Se ainda não houver transferências gravadas, adiciona os exemplos do Figma para visualização inicial
    if not historico_transferencias:
        historico_transferencias = [
            {"usuario_nome": "Valdimara", "de": "Tatuapé", "para": "Aricanduva", "data": "02/06/2025"},
            {"usuario_nome": "Souza", "de": "Aricanduva", "para": "Tatuapé", "data": "02/06/2025"},
            {"usuario_nome": "Júnior", "de": "Aricanduva", "para": "Iocuné", "data": "15/07/2025"},
        ]

    return templates.TemplateResponse(
        "usuarios/index.html",
        {
            "request": request,
            "usuario": usuario,
            "usuarios": usuarios,
            "lojas": lojas,
            "historico_transferencias": historico_transferencias,
            "sucesso": request.query_params.get("sucesso"),
        }
    )


@router.post("/transferir", response_class=HTMLResponse)
def transferir_usuario_loja(
    request: Request,
    usuario_id: int = Form(...),
    nova_loja_id: int = Form(...),
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Transfere colaborador para uma nova loja da rede (Figma Screen 9)."""
    user_alvo = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    nova_loja = db.query(Loja).filter(Loja.id == nova_loja_id).first()

    if not user_alvo or not nova_loja:
        raise HTTPException(status_code=400, detail="Usuário ou Loja não encontrados.")

    loja_anterior_nome = user_alvo.loja.nome.replace("Fellice ", "") if user_alvo.loja else "Sem filial"
    user_alvo.loja_id = nova_loja.id
    db.commit()

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=nova_loja.id,
        entidade="USUARIO",
        entidade_id=user_alvo.id,
        acao="TRANSFERENCIA_LOJA",
        dados_novos={
            "usuario_nome": user_alvo.nome,
            "loja_anterior": loja_anterior_nome,
            "loja_nova": nova_loja.nome.replace("Fellice ", ""),
        },
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/usuarios?sucesso=transferido", status_code=status.HTTP_302_FOUND)


@router.get("/novo", response_class=HTMLResponse)
def form_novo_usuario(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Formulário para cadastrar novo usuário."""
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    return templates.TemplateResponse(
        "usuarios/form.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "roles": [r.value for r in RoleEnum],
            "erro": None,
        }
    )


@router.post("/novo", response_class=HTMLResponse)
def salvar_novo_usuario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    role: str = Form(...),
    loja_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Cadastra novo usuário no sistema."""
    email_limpo = email.strip().lower()
    existente = db.query(Usuario).filter(Usuario.email == email_limpo).first()
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()

    if existente:
        return templates.TemplateResponse(
            "usuarios/form.html",
            {
                "request": request,
                "usuario": usuario,
                "lojas": lojas,
                "roles": [r.value for r in RoleEnum],
                "erro": f"E-mail '{email_limpo}' já está em uso.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        role_enum = RoleEnum(role)
    except ValueError:
        role_enum = RoleEnum.FUNCIONARIO

    loja_int_id = None
    if role_enum != RoleEnum.ADMIN and loja_id and loja_id.isdigit():
        loja_int_id = int(loja_id)

    novo_usuario = Usuario(
        nome=nome.strip(),
        email=email_limpo,
        senha_hash=hash_senha(senha),
        role=role_enum,
        loja_id=loja_int_id,
        ativo=True,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=novo_usuario.loja_id,
        entidade="USUARIO",
        entidade_id=novo_usuario.id,
        acao="CRIACAO",
        dados_novos={"email": novo_usuario.email, "role": novo_usuario.role.value},
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/usuarios", status_code=status.HTTP_302_FOUND)


@router.post("/{usuario_id}/status", response_class=HTMLResponse)
def alternar_status_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_admin),
):
    """Ativa ou inativa um usuário."""
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if u.id == usuario.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar seu próprio usuário.")

    u.ativo = not u.ativo
    db.commit()

    return RedirectResponse(url="/usuarios", status_code=status.HTTP_302_FOUND)
