from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.loja import Loja
from app.models.produto import Produto
from app.models.estoque import LojaProduto
from app.models.entrada import Entrada
from app.models.contagem import Contagem, ContagemItem
from app.models.fechamento import Fechamento, FechamentoItem, StatusFechamentoEnum


def obter_kpis_dashboard(db: Session, loja_id: Optional[int] = None) -> Dict[str, Any]:
    """Calcula os principais KPIs de desempenho e alertas de estoque."""
    hoje = datetime.now(timezone.utc).date()
    uma_semana_atras = datetime.now(timezone.utc) - timedelta(days=7)

    # Total de lojas
    total_lojas = db.query(func.count(Loja.id)).filter(Loja.ativa == True).scalar() or 0

    # Total de produtos
    total_produtos = db.query(func.count(Produto.id)).filter(Produto.ativo == True).scalar() or 0

    # Query base para estoque
    query_estoque = db.query(LojaProduto).filter(LojaProduto.ativo == True)
    if loja_id:
        query_estoque = query_estoque.filter(LojaProduto.loja_id == loja_id)

    itens_estoque = query_estoque.all()
    itens_baixo_estoque = sum(1 for item in itens_estoque if item.saldo_atual <= item.estoque_minimo)
    itens_zerados = sum(1 for item in itens_estoque if item.saldo_atual <= 0)

    # Entradas divergentes na última semana
    query_entradas_div = (
        db.query(func.count(Entrada.id))
        .filter(Entrada.divergente == True, Entrada.data_entrada >= uma_semana_atras)
    )
    if loja_id:
        query_entradas_div = query_entradas_div.filter(Entrada.loja_id == loja_id)
    total_divergencias_entradas = query_entradas_div.scalar() or 0

    # Fechamentos de hoje
    lojas = db.query(Loja).filter(Loja.ativa == True).all()
    status_lojas_fechamento = []
    for l in lojas:
        f_hoje = (
            db.query(Fechamento)
            .filter(Fechamento.loja_id == l.id, func.date(Fechamento.data_fechamento) == hoje)
            .first()
        )
        status_lojas_fechamento.append({
            "loja_id": l.id,
            "loja_nome": l.nome,
            "status": f_hoje.status.value if f_hoje else "PENDENTE",
            "turno": f_hoje.turno.value if f_hoje else "-",
        })

    return {
        "total_lojas": total_lojas,
        "total_produtos": total_produtos,
        "itens_baixo_estoque": itens_baixo_estoque,
        "itens_zerados": itens_zerados,
        "total_divergencias_entradas": total_divergencias_entradas,
        "status_lojas_fechamento": status_lojas_fechamento,
    }


def obter_relatorio_semanal(db: Session, loja_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Gera balanço de entradas e perdas dos últimos 7 dias agrupado por produto."""
    data_limite = datetime.now(timezone.utc) - timedelta(days=7)

    query_entradas = (
        db.query(
            Entrada.produto_id,
            Produto.nome.label("produto_nome"),
            Produto.unidade_medida,
            func.sum(Entrada.quantidade_recebida).label("total_recebido"),
            func.count(Entrada.id).label("total_cargas"),
        )
        .join(Produto, Entrada.produto_id == Produto.id)
        .filter(Entrada.data_entrada >= data_limite)
    )
    if loja_id:
        query_entradas = query_entradas.filter(Entrada.loja_id == loja_id)

    entradas_agrupadas = query_entradas.group_by(Entrada.produto_id, Produto.nome, Produto.unidade_medida).all()

    relatorio = []
    for e in entradas_agrupadas:
        relatorio.append({
            "produto_id": e.produto_id,
            "produto_nome": e.produto_nome,
            "unidade": e.unidade_medida.value,
            "total_recebido": round(float(e.total_recebido or 0), 3),
            "total_cargas": e.total_cargas,
        })
    return relatorio


def obter_relatorio_divergencias(
    db: Session, loja_id: Optional[int] = None, dias: int = 7
) -> List[Dict[str, Any]]:
    """Lista as maiores divergências e justificativas registradas em contagens físicas."""
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias)

    query = (
        db.query(ContagemItem)
        .join(Contagem, ContagemItem.contagem_id == Contagem.id)
        .join(Produto, ContagemItem.produto_id == Produto.id)
        .options(joinedload(ContagemItem.produto), joinedload(ContagemItem.contagem).joinedload(Contagem.loja))
        .filter(ContagemItem.divergente == True, Contagem.data_contagem >= data_limite)
        .order_by(func.abs(ContagemItem.diferenca).desc())
    )
    if loja_id:
        query = query.filter(Contagem.loja_id == loja_id)

    divergencias = query.limit(50).all()
    resultado = []
    for d in divergencias:
        resultado.append({
            "data": d.contagem.data_contagem.strftime("%d/%m/%Y %H:%M"),
            "loja": d.contagem.loja.nome if d.contagem.loja else "N/D",
            "produto": d.produto.nome if d.produto else "N/D",
            "unidade": d.produto.unidade_medida.value if d.produto else "UN",
            "esperado": round(d.quantidade_esperada, 3),
            "contado": round(d.quantidade_contada, 3),
            "diferenca": round(d.diferenca, 3),
            "observacao": d.observacao or "Sem justificativa",
        })
    return resultado


def obter_comparativo_lojas(db: Session) -> List[Dict[str, Any]]:
    """Gera tabela comparativa entre todas as lojas cadastradas (visão do Administrador)."""
    lojas = db.query(Loja).filter(Loja.ativa == True).all()
    uma_semana_atras = datetime.now(timezone.utc) - timedelta(days=7)
    comparativo = []

    for l in lojas:
        total_produtos = (
            db.query(func.count(LojaProduto.id))
            .filter(LojaProduto.loja_id == l.id, LojaProduto.ativo == True)
            .scalar() or 0
        )
        total_entradas_semana = (
            db.query(func.count(Entrada.id))
            .filter(Entrada.loja_id == l.id, Entrada.data_entrada >= uma_semana_atras)
            .scalar() or 0
        )
        total_divergencias_semana = (
            db.query(func.count(Entrada.id))
            .filter(Entrada.loja_id == l.id, Entrada.divergente == True, Entrada.data_entrada >= uma_semana_atras)
            .scalar() or 0
        )
        itens_criticos = (
            db.query(func.count(LojaProduto.id))
            .filter(LojaProduto.loja_id == l.id, LojaProduto.ativo == True, LojaProduto.saldo_atual <= LojaProduto.estoque_minimo)
            .scalar() or 0
        )

        comparativo.append({
            "loja_id": l.id,
            "nome": l.nome,
            "codigo": l.codigo,
            "total_produtos_catalogo": total_produtos,
            "entradas_semana": total_entradas_semana,
            "divergencias_semana": total_divergencias_semana,
            "itens_criticos": itens_criticos,
        })
    return comparativo
