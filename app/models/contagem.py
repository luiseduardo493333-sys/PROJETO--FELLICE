from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Contagem(Base):
    __tablename__ = "contagens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    data_contagem = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    observacao_geral = Column(Text, nullable=True)
    finalizada = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relacionamentos
    loja = relationship("Loja", back_populates="contagens")
    usuario = relationship("Usuario", back_populates="contagens")
    itens = relationship("ContagemItem", back_populates="contagem", cascade="all, delete-orphan")


class ContagemItem(Base):
    __tablename__ = "contagem_itens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    contagem_id = Column(Integer, ForeignKey("contagens.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)

    quantidade_esperada = Column(Float, nullable=False)
    quantidade_contada = Column(Float, nullable=False)
    diferenca = Column(Float, nullable=False)
    divergente = Column(Boolean, default=False, nullable=False, index=True)
    observacao = Column(Text, nullable=True)

    # Relacionamentos
    contagem = relationship("Contagem", back_populates="itens")
    produto = relationship("Produto", back_populates="contagem_itens")
