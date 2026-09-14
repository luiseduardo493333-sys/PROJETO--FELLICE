from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.models.estoque import LojaProduto
from app.models.produto import Produto
from app.models.loja import Loja


def obter_ou_criar_loja_produto(
    db: Session, loja_id: int, produto_id: int, estoque_minimo: float = 5.0, estoque_maximo: float = 50.0
) -> LojaProduto:
    """Garante o vínculo de um produto no catálogo da loja."""
    loja_prod = (
        db.query(LojaProduto)
        .filter(LojaProduto.loja_id == loja_id, LojaProduto.produto_id == produto_id)
        .first()
    )
    if not loja_prod:
        loja_prod = LojaProduto(
            loja_id=loja_id,
            produto_id=produto_id,
            estoque_minimo=estoque_minimo,
            estoque_maximo=estoque_maximo,
            saldo_atual=0.0,
            ativo=True,
        )
        db.add(loja_prod)
        db.commit()
        db.refresh(loja_prod)
    return loja_prod


def atualizar_saldo_entrada(
    db: Session, loja_id: int, produto_id: int, quantidade: float
) -> LojaProduto:
    """Incrementa o saldo físico/lógico em estoque após entrada de insumo."""
    loja_prod = (
        db.query(LojaProduto)
        .filter(LojaProduto.loja_id == loja_id, LojaProduto.produto_id == produto_id)
        .first()
    )
    if not loja_prod:
        loja_prod = LojaProduto(
            loja_id=loja_id,
            produto_id=produto_id,
            saldo_atual=quantidade,
            estoque_minimo=5.0,
            estoque_maximo=100.0,
            ativo=True,
        )
        db.add(loja_prod)
    else:
        loja_prod.saldo_atual = round(loja_prod.saldo_atual + quantidade, 3)

    db.commit()
    db.refresh(loja_prod)
    return loja_prod


def obter_estoque_loja(db: Session, loja_id: int) -> List[dict]:
    """Retorna a relação de produtos com saldos e alertas de reposição para a filial."""
    itens = (
        db.query(LojaProduto)
        .options(joinedload(LojaProduto.produto))
        .filter(LojaProduto.loja_id == loja_id, LojaProduto.ativo == True)
        .all()
    )

    resultado = []
    for item in itens:
        if not item.produto or not item.produto.ativo:
            continue
        alerta = item.saldo_atual <= item.estoque_minimo
        resultado.append({
            "loja_produto_id": item.id,
            "produto_id": item.produto_id,
            "nome": item.produto.nome,
            "categoria": item.produto.categoria,
            "unidade_medida": item.produto.unidade_medida.value,
            "codigo_sku": item.produto.codigo_sku,
            "saldo_atual": round(item.saldo_atual, 3),
            "estoque_minimo": item.estoque_minimo,
            "estoque_maximo": item.estoque_maximo,
            "alerta_reposicao": alerta,
            "status_estoque": "CRITICO" if item.saldo_atual == 0 else ("BAIXO" if alerta else "NORMAL"),
        })
    return resultado
