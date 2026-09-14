from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class UnidadeMedidaEnum(str, enum.Enum):
    UN = "UN"
    CX = "CX"
    PC = "PC"


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(120), unique=True, index=True, nullable=False)
    categoria = Column(String(80), nullable=False, index=True)
    unidade_medida = Column(Enum(UnidadeMedidaEnum), default=UnidadeMedidaEnum.UN, nullable=False)
    codigo_sku = Column(String(50), unique=True, index=True, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relacionamentos
    lojas_vinculadas = relationship("LojaProduto", back_populates="produto", cascade="all, delete-orphan")
    entradas = relationship("Entrada", back_populates="produto")
    contagem_itens = relationship("ContagemItem", back_populates="produto")
    fechamento_itens = relationship("FechamentoItem", back_populates="produto")
