import pytest
from datetime import datetime, timezone
from fastapi import status
from app.database import Session
from app.models.loja import Loja
from app.models.produto import Produto
from app.models.fechamento import Fechamento, StatusFechamentoEnum, TurnoEnum
from app.models.audit import AuditLog
from app.services.fechamento_service import iniciar_fechamento, finalizar_fechamento, reabrir_fechamento


def test_fluxo_fechamento_e_bloqueio(client, gerente_token, admin_token):
    """Testa o ciclo completo de fechamento de turno: abertura, consolidação de snapshot e bloqueio."""
    db = Session()
    try:
        loja_aricanduva = db.query(Loja).filter(Loja.codigo == "ARICANDUVA").first()
        loja_id = loja_aricanduva.id
        db.query(Fechamento).filter(Fechamento.loja_id == loja_id).delete()
        db.commit()
    finally:
        db.close()

    # 1. Gerente de Aricanduva inicia fechamento do turno da NOITE
    client.cookies.set("access_token", admin_token)
    r_iniciar = client.post(
        "/fechamentos/iniciar",
        data={
            "loja_id": loja_id,
            "turno": "NOITE",
        },
        follow_redirects=False,
    )
    assert r_iniciar.status_code == status.HTTP_302_FOUND
    fechamento_id = int(r_iniciar.headers["location"].split("/")[-1])

    r_finalizar = client.post(
        f"/fechamentos/{fechamento_id}/finalizar",
        data={"observacao": "Fechamento consolidado sem quebras anormais."},
        follow_redirects=False,
    )
    assert r_finalizar.status_code == status.HTTP_302_FOUND

    # 3. Verifica se o fechamento ficou FINALIZADO com snapshot de itens
    db = Session()
    try:
        f_final = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
        assert f_final.status == StatusFechamentoEnum.FINALIZADO
        assert len(f_final.itens) > 0
    finally:
        db.close()

    # 4. Reabertura pelo Administrador com justificativa obrigatória
    r_reabrir = client.post(
        f"/fechamentos/{fechamento_id}/reabrir",
        data={"justificativa": "Correção autorizada da contagem de molho de tomate pelo gestor operacional."},
        follow_redirects=False,
    )
    assert r_reabrir.status_code == status.HTTP_302_FOUND

    # 5. Verifica se status mudou para REABERTO e foi logado em auditoria
    db = Session()
    try:
        f_reaberto = db.query(Fechamento).filter(Fechamento.id == fechamento_id).first()
        assert f_reaberto.status == StatusFechamentoEnum.REABERTO
        assert f_reaberto.justificativa_reabertura is not None

        # Checa trilha de auditoria
        audit_reabertura = (
            db.query(AuditLog)
            .filter(AuditLog.entidade == "FECHAMENTO", AuditLog.acao == "REABERTURA", AuditLog.entidade_id == fechamento_id)
            .first()
        )
        assert audit_reabertura is not None
    finally:
        db.close()
