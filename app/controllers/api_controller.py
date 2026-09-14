from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.loja import Loja
from app.models.produto import Produto, UnidadeMedidaEnum
from app.models.estoque import LojaProduto
from app.models.entrada import Entrada
from app.models.fechamento import Fechamento, TurnoEnum
from app.auth import (
    verificar_senha,
    criar_token,
    decodificar_token,
    get_usuario_logado,
    validar_acesso_loja,
)
from app.services.estoque_service import obter_estoque_loja, atualizar_saldo_entrada
from app.services.fechamento_service import iniciar_fechamento, finalizar_fechamento
from app.services.relatorio_service import (
    obter_kpis_dashboard,
    obter_relatorio_semanal,
    obter_relatorio_divergencias,
    obter_comparativo_lojas,
)

router = APIRouter(prefix="/api/v1", tags=["API REST"])


# Schemas Pydantic para a API REST
class LoginSchema(BaseModel):
    email: str
    senha: str


class EntradaSchema(BaseModel):
    produto_id: int
    quantidade_recebida: float
    quantidade_esperada: Optional[float] = None
    fornecedor: Optional[str] = None
    nota_fiscal: Optional[str] = None
    motivo_divergencia: Optional[str] = None


class FechamentoIniciarSchema(BaseModel):
    turno: str = "NOITE"


@router.post("/auth/login")
def api_login(payload: LoginSchema, db: Session = Depends(get_db)):
    """Endpoint REST para autenticação via JSON retornando JWT."""
    usuario = db.query(Usuario).filter(Usuario.email == payload.email.strip().lower()).first()
    if not usuario or not verificar_senha(payload.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    token = criar_token({
        "sub": str(usuario.id),
        "email": usuario.email,
        "role": usuario.role.value,
        "loja_id": usuario.loja_id,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "role": usuario.role.value,
            "loja_id": usuario.loja_id,
        },
    }


@router.get("/lojas")
def api_listar_lojas(db: Session = Depends(get_db), usuario = Depends(get_usuario_logado)):
    """Lista lojas ativas."""
    if usuario.role == RoleEnum.ADMIN:
        lojas = db.query(Loja).filter(Loja.ativa == True).all()
    else:
        lojas = db.query(Loja).filter(Loja.id == usuario.loja_id).all()
    return [{"id": l.id, "nome": l.nome, "codigo": l.codigo, "endereco": l.endereco} for l in lojas]


@router.get("/produtos")
def api_listar_produtos(db: Session = Depends(get_db), usuario = Depends(get_usuario_logado)):
    """Lista catálogo geral de produtos."""
    produtos = db.query(Produto).filter(Produto.ativo == True).all()
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "categoria": p.categoria,
            "unidade_medida": p.unidade_medida.value,
            "codigo_sku": p.codigo_sku,
        }
        for p in produtos
    ]


@router.get("/lojas/{loja_id}/estoque")
def api_obter_estoque(loja_id: int, db: Session = Depends(get_db), usuario = Depends(get_usuario_logado)):
    """Consulta saldo em tempo real de uma filial."""
    validar_acesso_loja(loja_id, usuario)
    return obter_estoque_loja(db, loja_id=loja_id)


@router.post("/lojas/{loja_id}/entradas")
def api_registrar_entrada(
    loja_id: int,
    payload: EntradaSchema,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado),
):
    """Registra entrada de produto via REST."""
    validar_acesso_loja(loja_id, usuario)
    diferenca = 0.0
    divergente = False
    if payload.quantidade_esperada is not None and abs(payload.quantidade_recebida - payload.quantidade_esperada) > 0.001:
        divergente = True
        diferenca = round(payload.quantidade_recebida - payload.quantidade_esperada, 3)
        if not payload.motivo_divergencia:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Divergência detectada: motivo_divergencia é obrigatório."
            )

    entrada = Entrada(
        loja_id=loja_id,
        produto_id=payload.produto_id,
        usuario_id=usuario.id,
        quantidade_recebida=payload.quantidade_recebida,
        quantidade_esperada=payload.quantidade_esperada,
        diferenca=diferenca,
        divergente=divergente,
        motivo_divergencia=payload.motivo_divergencia,
        fornecedor=payload.fornecedor,
        nota_fiscal=payload.nota_fiscal,
    )
    db.add(entrada)
    atualizar_saldo_entrada(db, loja_id=loja_id, produto_id=payload.produto_id, quantidade=payload.quantidade_recebida)
    db.commit()
    db.refresh(entrada)
    return {"status": "sucesso", "entrada_id": entrada.id, "divergente": divergente, "diferenca": diferenca}


@router.get("/dashboard/kpis")
def api_kpis(loja_id: Optional[int] = None, db: Session = Depends(get_db), usuario = Depends(get_usuario_logado)):
    """Indicadores KPI do dashboard."""
    alvo = loja_id if usuario.role == RoleEnum.ADMIN else usuario.loja_id
    return obter_kpis_dashboard(db, loja_id=alvo)


@router.get("/relatorios/comparativo")
def api_comparativo(db: Session = Depends(get_db), usuario = Depends(get_usuario_logado)):
    """Comparativo entre filiais (Admin)."""
    if usuario.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao Administrador.")
    return obter_comparativo_lojas(db)
