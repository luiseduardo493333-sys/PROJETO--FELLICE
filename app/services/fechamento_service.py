from datetime import datetime, timezone, date
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.fechamento import Fechamento, FechamentoItem, StatusFechamentoEnum, TurnoEnum
from app.models.estoque import LojaProduto
from app.models.entrada import Entrada
from app.models.contagem import Contagem, ContagemItem
from app.services.audit_service import registrar_auditoria


def verificar_bloqueio_fechamento(db: Session, loja_id: int, data_ref: date, turno: TurnoEnum = TurnoEnum.NOITE):
    """
    Verifica se já existe fechamento FINALIZADO para a loja, data e turno.
    Se existir, bloqueia alterações nos registros daquele período.
    """
    fechamento = (
        db.query(Fechamento)
        .filter(
            Fechamento.loja_id == loja_id,
            func.date(Fechamento.data_fechamento) == data_ref,
            Fechamento.turno == turno,
            Fechamento.status == StatusFechamentoEnum.FINALIZADO,
        )
        .first()
    )
    if fechamento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operação bloqueada: O turno {turno.value} da loja em {data_ref} já foi FINALIZADO. Reabra o fechamento para autorizar modificações.",
        )


def iniciar_fechamento(
    db: Session, loja_id: int, usuario_id: int, turno: TurnoEnum = TurnoEnum.NOITE
) -> Fechamento:
    """Abre uma sessão de fechamento diário/turno para a loja."""
    hoje = datetime.now(timezone.utc).date()

    # Verifica se já existe fechamento para hoje e turno
    existente = (
        db.query(Fechamento)
        .filter(
            Fechamento.loja_id == loja_id,
            func.date(Fechamento.data_fechamento) == hoje,
            Fechamento.turno == turno,
        )
        .first()
    )

    if existente:
        if existente.status == StatusFechamentoEnum.FINALIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O fechamento para {hoje} no turno {turno.value} já está finalizado.",
            )
        return existente

    fechamento = Fechamento(
        loja_id=loja_id,
        usuario_id=usuario_id,
        data_fechamento=datetime.now(timezone.utc),
        turno=turno,
        status=StatusFechamentoEnum.EM_ANDAMENTO,
    )
    db.add(fechamento)
    db.commit()
    db.refresh(fechamento)

    registrar_auditoria(
        db=db,
        usuario_id=usuario_id,
        loja_id=loja_id,
        entidade="FECHAMENTO",
        entidade_id=fechamento.id,
        acao="CRIACAO",
        dados_novos={"loja_id": loja_id, "turno": turno.value, "status": "EM_ANDAMENTO"},
    )
    return fechamento


def finalizar_fechamento(db: Session, fechamento_id: int, usuario_id: int) -> Fechamento:
    """
    Consolida e congela os itens do fechamento:
    - Lê a contagem física mais recente do dia.
    - Totaliza entradas ocorridas no turno/dia.
    - Grava o snapshot em fechamento_itens.
    - Atualiza saldo atual do estoque para a contagem física apurada.
    - Congela o fechamento como FINALIZADO.
    """
    fechamento = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
    if not fechamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento não encontrado.")

    if fechamento.status == StatusFechamentoEnum.FINALIZADO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fechamento já está finalizado.")

    loja_id = fechamento.loja_id
    data_ref = fechamento.data_fechamento.date()

    # Limpa itens prévios se estava em rascunho
    db.query(FechamentoItem).filter(FechamentoItem.fechamento_id == fechamento.id).delete()

    # Busca produtos ativos da filial
    catalogo = (
        db.query(LojaProduto)
        .filter(LojaProduto.loja_id == loja_id, LojaProduto.ativo == True)
        .all()
    )

    # Busca a última contagem do dia
    ultima_contagem = (
        db.query(Contagem)
        .filter(Contagem.loja_id == loja_id, func.date(Contagem.data_contagem) == data_ref)
        .order_by(Contagem.id.desc())
        .first()
    )

    contagens_map = {}
    if ultima_contagem:
        itens_c = db.query(ContagemItem).filter(ContagemItem.contagem_id == ultima_contagem.id).all()
        for c in itens_c:
            contagens_map[c.produto_id] = (c.quantidade_contada, c.observacao)

    for item in catalogo:
        # Total de entradas do dia para este produto
        total_entradas = (
            db.query(func.coalesce(func.sum(Entrada.quantidade_recebida), 0.0))
            .filter(
                Entrada.loja_id == loja_id,
                Entrada.produto_id == item.produto_id,
                func.date(Entrada.data_entrada) == data_ref,
            )
            .scalar()
        )

        contagem_info = contagens_map.get(item.produto_id)
        if contagem_info:
            contagem_final = contagem_info[0]
            obs = contagem_info[1]
        else:
            contagem_final = item.saldo_atual
            obs = "Contagem não informada; saldo lógico mantido."

        # Diferença / perda calculada:
        # Estoque esperado = saldo atual anterior.
        # Diferença = contagem_final - saldo_atual
        diferenca = round(contagem_final - item.saldo_atual, 3)

        f_item = FechamentoItem(
            fechamento_id=fechamento.id,
            produto_id=item.produto_id,
            saldo_inicial=item.saldo_atual,
            total_entradas=float(total_entradas),
            contagem_final=contagem_final,
            diferenca=diferenca,
            observacao=obs,
        )
        db.add(f_item)

        # Atualiza o saldo do estoque para a contagem final
        item.saldo_atual = contagem_final

    fechamento.status = StatusFechamentoEnum.FINALIZADO
    fechamento.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(fechamento)

    registrar_auditoria(
        db=db,
        usuario_id=usuario_id,
        loja_id=loja_id,
        entidade="FECHAMENTO",
        entidade_id=fechamento.id,
        acao="FECHAMENTO",
        dados_novos={"status": "FINALIZADO", "itens_congelados": len(catalogo)},
    )
    return fechamento


def reabrir_fechamento(
    db: Session, fechamento_id: int, usuario_id: int, justificativa: str
) -> Fechamento:
    """Reabre um fechamento bloqueado mediante justificativa obrigatória."""
    fechamento = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
    if not fechamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fechamento não encontrado.")

    if fechamento.status != StatusFechamentoEnum.FINALIZADO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Apenas fechamentos finalizados podem ser reabertos.")

    if not justificativa or len(justificativa.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Justificativa de reabertura é obrigatória e deve ser detalhada.",
        )

    fechamento.status = StatusFechamentoEnum.REABERTO
    fechamento.reaberto_por_id = usuario_id
    fechamento.justificativa_reabertura = justificativa.strip()

    db.commit()
    db.refresh(fechamento)

    registrar_auditoria(
        db=db,
        usuario_id=usuario_id,
        loja_id=fechamento.loja_id,
        entidade="FECHAMENTO",
        entidade_id=fechamento.id,
        acao="REABERTURA",
        dados_novos={"justificativa": justificativa, "status": "REABERTO"},
    )
    return fechamento
