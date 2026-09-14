from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Loja(Base):
    __tablename__ = "lojas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True, index=True)
    codigo = Column(String(30), nullable=False, unique=True, index=True)
    endereco = Column(String(255), nullable=True)
    telefone = Column(String(50), nullable=True)
    ativa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relacionamentos
    usuarios = relationship("Usuario", back_populates="loja")
    produtos_vinculados = relationship("LojaProduto", back_populates="loja", cascade="all, delete-orphan")
    entradas = relationship("Entrada", back_populates="loja")
    contagens = relationship("Contagem", back_populates="loja")
    fechamentos = relationship("Fechamento", back_populates="loja")
