from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto import Produto, UnidadeMedidaEnum
from app.models.loja import Loja
from app.models.estoque import LojaProduto
from app.models.usuario import RoleEnum
from app.auth import get_usuario_logado, get_gerente_ou_admin
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/produtos", tags=["Produtos"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_produtos(
    request: Request,
    busca: str = "",
    categoria: str = "",
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Lista catálogo geral de produtos com opção de filtragem."""
    query = db.query(Produto).filter(Produto.ativo == True)

    if busca:
        query = query.filter(Produto.nome.ilike(f"%{busca}%"))
    if categoria:
        query = query.filter(Produto.categoria == categoria)

    produtos = query.order_by(Produto.categoria, Produto.nome).all()

    # Categorias únicas para filtro
    categorias = [c[0] for c in db.query(Produto.categoria).distinct().all()]

    return templates.TemplateResponse(
        "produtos/index.html",
        {
            "request": request,
            "usuario": usuario,
            "produtos": produtos,
            "busca": busca,
            "categoria_selecionada": categoria,
            "categorias": categorias,
            "unidades": [u.value for u in UnidadeMedidaEnum],
        }
    )


@router.get("/novo", response_class=HTMLResponse)
def form_novo_produto(
    request: Request,
    usuario = Depends(get_gerente_ou_admin),
):
    """Exibe formulário de cadastro de novo produto global."""
    return templates.TemplateResponse(
        "produtos/form.html",
        {
            "request": request,
            "usuario": usuario,
            "produto": None,
            "unidades": [u.value for u in UnidadeMedidaEnum],
            "erro": None,
        }
    )


@router.post("/novo", response_class=HTMLResponse)
def salvar_novo_produto(
    request: Request,
    nome: str = Form(...),
    categoria: str = Form(...),
    unidade_medida: str = Form(...),
    codigo_sku: Optional[str] = Form(None),
    estoque_minimo_padrao: float = Form(5.0),
    estoque_maximo_padrao: float = Form(50.0),
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Cadastra novo produto e cria vínculo automático nas lojas ativas."""
    nome_limpo = nome.strip()
    existente = db.query(Produto).filter(Produto.nome.ilike(nome_limpo)).first()
    if existente:
        return templates.TemplateResponse(
            "produtos/form.html",
            {
                "request": request,
                "usuario": usuario,
                "produto": None,
                "unidades": [u.value for u in UnidadeMedidaEnum],
                "erro": f"Produto '{nome_limpo}' já está cadastrado no sistema.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        unidade_enum = UnidadeMedidaEnum(unidade_medida)
    except ValueError:
        unidade_enum = UnidadeMedidaEnum.UN

    novo_prod = Produto(
        nome=nome_limpo,
        categoria=categoria.strip(),
        unidade_medida=unidade_enum,
        codigo_sku=codigo_sku.strip() if codigo_sku else None,
        ativo=True,
    )
    db.add(novo_prod)
    db.commit()
    db.refresh(novo_prod)

    # Vincula o novo produto em todas as lojas ativas com estoque zero
    lojas = db.query(Loja).filter(Loja.ativa == True).all()
    for l in lojas:
        loja_prod = LojaProduto(
            loja_id=l.id,
            produto_id=novo_prod.id,
            estoque_minimo=estoque_minimo_padrao,
            estoque_maximo=estoque_maximo_padrao,
            saldo_atual=0.0,
            ativo=True,
        )
        db.add(loja_prod)
    db.commit()

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=usuario.loja_id,
        entidade="PRODUTO",
        entidade_id=novo_prod.id,
        acao="CRIACAO",
        dados_novos={"nome": novo_prod.nome, "unidade": novo_prod.unidade_medida.value},
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/produtos", status_code=status.HTTP_302_FOUND)


@router.get("/{produto_id}/editar", response_class=HTMLResponse)
def form_editar_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Formulário de edição de produto."""
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    return templates.TemplateResponse(
        "produtos/form.html",
        {
            "request": request,
            "usuario": usuario,
            "produto": produto,
            "unidades": [u.value for u in UnidadeMedidaEnum],
            "erro": None,
        }
    )


@router.post("/{produto_id}/editar", response_class=HTMLResponse)
def salvar_edicao_produto(
    produto_id: int,
    request: Request,
    nome: str = Form(...),
    categoria: str = Form(...),
    unidade_medida: str = Form(...),
    codigo_sku: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    usuario = Depends(get_gerente_ou_admin),
):
    """Salva atualizações nos dados do produto."""
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    dados_antigos = {"nome": produto.nome, "categoria": produto.categoria, "sku": produto.codigo_sku}

    produto.nome = nome.strip()
    produto.categoria = categoria.strip()
    produto.codigo_sku = codigo_sku.strip() if codigo_sku else None
    try:
        produto.unidade_medida = UnidadeMedidaEnum(unidade_medida)
    except ValueError:
        pass

    db.commit()

    registrar_auditoria(
        db=db,
        usuario_id=usuario.id,
        loja_id=usuario.loja_id,
        entidade="PRODUTO",
        entidade_id=produto.id,
        acao="EDICAO",
        dados_anteriores=dados_antigos,
        dados_novos={"nome": produto.nome, "categoria": produto.categoria, "sku": produto.codigo_sku},
        ip_origem=request.client.host if request.client else None,
    )

    return RedirectResponse(url="/produtos", status_code=status.HTTP_302_FOUND)
