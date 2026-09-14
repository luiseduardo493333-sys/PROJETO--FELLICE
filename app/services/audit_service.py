import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def registrar_auditoria(
    db: Session,
    usuario_id: Optional[int],
    loja_id: Optional[int],
    entidade: str,
    entidade_id: Optional[int],
    acao: str,
    dados_anteriores: Optional[Any] = None,
    dados_novos: Optional[Any] = None,
    ip_origem: Optional[str] = None,
) -> AuditLog:
    """Registra uma trilha indelével de auditoria no sistema."""
    old_str = json.dumps(dados_anteriores, default=str, ensure_ascii=False) if dados_anteriores else None
    new_str = json.dumps(dados_novos, default=str, ensure_ascii=False) if dados_novos else None

    log = AuditLog(
        usuario_id=usuario_id,
        loja_id=loja_id,
        entidade=entidade,
        entidade_id=entidade_id,
        acao=acao,
        dados_anteriores=old_str,
        dados_novos=new_str,
        ip_origem=ip_origem,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
