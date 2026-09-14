from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class LojaProduto(Base):
    __tablename__ = "loja_produtos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)
    estoque_minimo = Column(Float, default=0.0, nullable=False)
    estoque_maximo = Column(Float, default=100.0, nullable=False)
    saldo_atual = Column(Float, default=0.0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("loja_id", "produto_id", name="uq_loja_produto"),
    )

    # Relacionamentos
    loja = relationship("Loja", back_populates="produtos_vinculados")
    produto = relationship("Produto", back_populates="lojas_vinculadas")
