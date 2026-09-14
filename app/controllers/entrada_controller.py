from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models.entrada import Entrada
from app.models.produto import Produto
from app.models.loja import Loja
from app.models.usuario import RoleEnum
from app.models.estoque import LojaProduto
from app.auth import get_usuario_logado, validar_acesso_loja
from app.services.estoque_service import atualizar_saldo_entrada
from app.services.fechamento_service import verificar_bloqueio_fechamento
from app.services.audit_service import registrar_auditoria

router = APIRouter(prefix="/entradas", tags=["Entradas"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def listar_entradas(
    request: Request,
    loja_id: Optional[int] = None,
    apenas_divergentes: Optional[bool] = False,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Lista histórico de entradas de produtos com filtros."""
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

    query = db.query(Entrada).options(joinedload(Entrada.produto), joinedload(Entrada.loja), joinedload(Entrada.usuario))
    if loja_alvo_id:
        query = query.filter(Entrada.loja_id == loja_alvo_id)
    if apenas_divergentes:
        query = query.filter(Entrada.divergente == True)

    entradas = query.order_by(Entrada.data_entrada.desc()).limit(100).all()
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    produtos = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.nome).all()

    total_entradas = len(entradas)
    total_divergentes = sum(1 for e in entradas if e.divergente)

    return templates.TemplateResponse(
        "entradas/index.html",
        {
            "request": request,
            "usuario": usuario,
            "entradas": entradas,
            "lojas": lojas,
            "produtos": produtos,
            "loja_alvo_id": loja_alvo_id,
            "apenas_divergentes": apenas_divergentes,
            "total_entradas": total_entradas,
            "total_divergentes": total_divergentes,
        }
    )


@router.get("/novo", response_class=HTMLResponse)
def form_nova_entrada(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Exibe formulário para dar entrada em mercadorias recebidas (Figma Screen 4)."""
    lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
    produtos = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.nome).all()

    loja_padrao_id = usuario.loja_id
    if not loja_padrao_id and lojas:
        cookie_loja = request.cookies.get("loja_ativa_id")
        loja_padrao_id = int(cookie_loja) if cookie_loja and cookie_loja.isdigit() else lojas[0].id

    loja_atual = db.query(Loja).filter(Loja.id == loja_padrao_id).first() if loja_padrao_id else None

    return templates.TemplateResponse(
        "entradas/form.html",
        {
            "request": request,
            "usuario": usuario,
            "lojas": lojas,
            "loja_atual": loja_atual,
            "produtos": produtos,
            "loja_padrao_id": loja_padrao_id,
            "erro": None,
        }
    )


@router.post("/novo", response_class=HTMLResponse)
async def salvar_nova_entrada(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Registra entradas de insumos (compatível com item único e multi-itens do Figma)."""
    form_data = await request.form()
    loja_id_raw = form_data.get("loja_id")
    if not loja_id_raw:
        raise HTTPException(status_code=400, detail="Loja não informada.")
    loja_id = int(loja_id_raw)

    validar_acesso_loja(loja_id, usuario)
    hoje = datetime.now(timezone.utc).date()

    # Validação de bloqueio caso fechamento do dia já tenha sido concluído
    verificar_bloqueio_fechamento(db, loja_id=loja_id, data_ref=hoje)

    # Identifica listas de produtos (suporta 'produto_ids[]' ou 'produto_id')
    produto_ids = form_data.getlist("produto_ids[]") or form_data.getlist("produto_id")
    quantidades_recebidas = form_data.getlist("quantidades[]") or form_data.getlist("quantidade_recebida")
    quantidades_esperadas = form_data.getlist("quantidades_esperadas[]") or form_data.getlist("quantidade_esperada")
    motivos_divergencia = form_data.getlist("motivos_divergencia[]") or form_data.getlist("motivo_divergencia")
    fornecedor = form_data.get("fornecedor")
    nota_fiscal = form_data.get("nota_fiscal")

    if not produto_ids:
        raise HTTPException(status_code=400, detail="Nenhum produto informado na entrada.")

    # Processa cada item enviado
    for i, p_id_str in enumerate(produto_ids):
        if not p_id_str:
            continue
        p_id = int(p_id_str)
        qtd_rec = float(quantidades_recebidas[i]) if i < len(quantidades_recebidas) and quantidades_recebidas[i] else 0.0
        qtd_esp = float(quantidades_esperadas[i]) if i < len(quantidades_esperadas) and quantidades_esperadas[i] else None
        motivo = motivos_divergencia[i] if i < len(motivos_divergencia) and motivos_divergencia[i] else None

        divergente = False
        diferenca = 0.0
        if qtd_esp is not None and abs(qtd_rec - qtd_esp) > 0.001:
            divergente = True
            diferenca = round(qtd_rec - qtd_esp, 3)

            # Regra de negócio: Justificativa obrigatória se houver divergência
            if not motivo or len(motivo.strip()) < 4:
                lojas = db.query(Loja).filter(Loja.ativa == True).order_by(Loja.nome).all()
                produtos = db.query(Produto).filter(Produto.ativo == True).order_by(Produto.nome).all()
                loja_atual = db.query(Loja).filter(Loja.id == loja_id).first()
                return templates.TemplateResponse(
                    "entradas/form.html",
                    {
                        "request": request,
                        "usuario": usuario,
                        "lojas": lojas,
                        "loja_atual": loja_atual,
                        "produtos": produtos,
                        "loja_padrao_id": loja_id,
                        "erro": "Divergência detectada! O preenchimento do motivo/justificativa é obrigatório quando o recebido difere do esperado.",
                    },
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        entrada = Entrada(
            loja_id=loja_id,
            produto_id=p_id,
            usuario_id=usuario.id,
            quantidade_recebida=qtd_rec,
            quantidade_esperada=qtd_esp,
            diferenca=diferenca,
            divergente=divergente,
            motivo_divergencia=motivo.strip() if motivo else None,
            fornecedor=fornecedor.strip() if fornecedor else None,
            nota_fiscal=nota_fiscal.strip() if nota_fiscal else None,
            data_entrada=datetime.now(timezone.utc),
        )
        db.add(entrada)

        # Atualiza o saldo do estoque na filial
        atualizar_saldo_entrada(db, loja_id=loja_id, produto_id=p_id, quantidade=qtd_rec)
        db.commit()
        db.refresh(entrada)

        registrar_auditoria(
            db=db,
            usuario_id=usuario.id,
            loja_id=loja_id,
            entidade="ENTRADA",
            entidade_id=entrada.id,
            acao="CRIACAO",
            dados_novos={
                "produto_id": p_id,
                "qtd_recebida": qtd_rec,
                "divergente": divergente,
                "diferenca": diferenca,
            },
            ip_origem=request.client.host if request.client else None,
        )

    return RedirectResponse(url="/entradas", status_code=status.HTTP_302_FOUND)
