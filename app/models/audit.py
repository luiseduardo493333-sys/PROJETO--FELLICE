from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="SET NULL"), nullable=True, index=True)

    entidade = Column(String(50), nullable=False, index=True)
    entidade_id = Column(Integer, nullable=True, index=True)
    acao = Column(String(50), nullable=False, index=True)

    dados_anteriores = Column(Text, nullable=True)  # JSON string
    dados_novos = Column(Text, nullable=True)       # JSON string
    ip_origem = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relacionamento
    usuario = relationship("Usuario", back_populates="audit_logs")
