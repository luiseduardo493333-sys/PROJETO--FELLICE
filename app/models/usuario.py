from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    FUNCIONARIO = "FUNCIONARIO"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.FUNCIONARIO, nullable=False)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="SET NULL"), nullable=True, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relacionamentos
    loja = relationship("Loja", back_populates="usuarios")
    entradas = relationship("Entrada", back_populates="usuario")
    contagens = relationship("Contagem", back_populates="usuario")
    fechamentos = relationship("Fechamento", foreign_keys="Fechamento.usuario_id", back_populates="usuario")
    audit_logs = relationship("AuditLog", back_populates="usuario")
