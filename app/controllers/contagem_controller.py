from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.contagem import Contagem, ContagemItem
from app.models.loja import Loja
from app.models.produto import Produto
from app.models.estoque import LojaProduto
from app.models.usuario import RoleEnum
from app.auth import get_usuario_logado, validar_acesso_loja
from app.services.fechamento_service import verificar_bloqueio_fechamento
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/contagens", tags=["Contagens"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_contagens(
    request: Request,
    loja_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Lista histórico de contagens diárias realizadas."""
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

    query = db.query(Contagem).options(joinedload(Contagem.loja), joinedload(Contagem.usuario), joinedload(Contagem.itens))
    if loja_alvo_id:
        query = query.filter(Contagem.loja_id == loja_alvo_id)

    contagens = query.order_by(Contagem.data_contagem.desc()).limit(50).all()
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()

    loja_contagem_id = loja_alvo_id or (lojas[0].id if lojas else 1)
    loja_atual = db.query(Loja).filter(Loja.id == loja_contagem_id).first()
    itens = (
        db.query(LojaProduto)
        .options(joinedload(LojaProduto.produto))
        .filter(LojaProduto.loja_id == loja_contagem_id, LojaProduto.ativo == True)
        .all()
    )

    return templates.TemplateResponse(
        "contagens/index.html",
        {
            "request": request,
            "usuario": usuario,
            "contagens": contagens,
            "lojas": lojas,
            "loja_alvo_id": loja_alvo_id,
            "loja_atual": loja_atual,
            "itens": itens,
        }
    )


@router.get("/novo", response_class=HTMLResponse)
def form_nova_contagem(
    request: Request,
    loja_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """
    Tela de contagem física diária:
    Exibe a tabela de produtos ativos da loja com o estoque esperado
    para o funcionário digitar a quantidade física encontrada.
    """
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

    # Busca catálogo e saldo atual de estoque
    itens = (
        db.query(LojaProduto)
        .options(joinedload(LojaProduto.produto))
        .filter(LojaProduto.loja_id == loja_alvo_id, LojaProduto.ativo == True)
        .all()
    )

    return templates.TemplateResponse(
        "contagens/form.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "itens": itens,
            "erro": None,
        }
    )


@router.post("/novo", response_class=HTMLResponse)
async def salvar_nova_contagem(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Recebe as contagens físicas digitadas, compara com estoque esperado e registra."""
    form = await request.form()
    loja_id = int(form.get("loja_id"))
    validar_acesso_loja(loja_id, usuario)

    hoje = datetime.now(timezone.utc).date()
    verificar_bloqueio_fechamento(db, loja_id=loja_id, data_ref=hoje)

    observacao_geral = form.get("observacao_geral", "").strip()

    # Cria registro principal da contagem
    contagem = Contagem(
        loja_id=loja_id,
        usuario_id=usuario.id,
        data_contagem=datetime.now(timezone.utc),
        observacao_geral=observacao_geral if observacao_geral else None,
        finalizada=True,
    )
    db.add(contagem)
    db.commit()
    db.refresh(contagem)

    # Processa cada item enviado no formulário
    itens_catalogo = (
        db.query(LojaProduto)
        .filter(LojaProduto.loja_id == loja_id, LojaProduto.ativo == True)
        .all()
    )

    divergencias_encontradas = 0

    for item in itens_catalogo:
        campo_qtd = f"contagem_{item.produto_id}"
        campo_obs = f"obs_{item.produto_id}"

        if campo_qtd in form and form.get(campo_qtd).strip() != "":
            qtd_contada = float(form.get(campo_qtd).replace(",", "."))
            obs_item = form.get(campo_obs, "").strip()
            esperado = item.saldo_atual
            diferenca = round(qtd_contada - esperado, 3)
            divergente = abs(diferenca) > 0.001

            if divergente:
                divergencias_encontradas += 1

            c_item = ContagemItem(
                contagem_id=contagem.id,
                produto_id=item.produto_id,
                quantidade_esperada=esperado,
                quantidade_contada=qtd_contada,
                diferenca=diferenca,
                divergente=divergente,
                observacao=obs_item if obs_item else None,
            )
            db.add(c_item)

    db.commit()

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=loja_id,
        entidade="CONTAGEM",
        entidade_id=contagem.id,
        acao="CRIACAO",
        dados_novos={"divergencias": divergencias_encontradas, "contagem_id": contagem.id},
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url=f"/contagens/{contagem.id}", status_code=status.HTTP_302_FOUND)


@router.get("/{contagem_id}", response_class=HTMLResponse)
def detalhes_contagem(
    contagem_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Exibe resultado detalhado da contagem física com confronto de divergências."""
    contagem = (
        db.query(Contagem)
        .options(
            joinedload(Contagem.loja),
            joinedload(Contagem.usuario),
            joinedload(Contagem.itens).joinedload(ContagemItem.produto),
        )
        .filter(Contagem.id == contagem_id)
        .first()
    )
    if not contagem:
        raise HTTPException(status_code=404, detail="Contagem não encontrada.")

    validar_acesso_loja(contagem.loja_id, usuario)

    total_divergentes = sum(1 for item in contagem.itens if item.divergente)

    return templates.TemplateResponse(
        "contagens/detalhes.html",
        {
            "request": request,
            "usuario": usuario,
            "contagem": contagem,
            "total_divergentes": total_divergentes,
        }
    )
