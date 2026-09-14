from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Entrada(Base):
    __tablename__ = "entradas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    quantidade_recebida = Column(Float, nullable=False)
    quantidade_esperada = Column(Float, nullable=True)
    diferenca = Column(Float, default=0.0, nullable=False)
    divergente = Column(Boolean, default=False, nullable=False, index=True)
    motivo_divergencia = Column(Text, nullable=True)

    fornecedor = Column(String(120), nullable=True)
    nota_fiscal = Column(String(60), nullable=True)
    data_entrada = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relacionamentos
    loja = relationship("Loja", back_populates="entradas")
    produto = relationship("Produto", back_populates="entradas")
    usuario = relationship("Usuario", back_populates="entradas")
