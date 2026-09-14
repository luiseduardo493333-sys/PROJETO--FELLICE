from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class StatusFechamentoEnum(str, enum.Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    FINALIZADO = "FINALIZADO"
    REABERTO = "REABERTO"


class TurnoEnum(str, enum.Enum):
    DIA = "DIA"
    NOITE = "NOITE"
    UNICO = "UNICO"


class Fechamento(Base):
    __tablename__ = "fechamentos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loja_id = Column(Integer, ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    data_fechamento = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    turno = Column(Enum(TurnoEnum), default=TurnoEnum.NOITE, nullable=False)
    status = Column(Enum(StatusFechamentoEnum), default=StatusFechamentoEnum.EM_ANDAMENTO, nullable=False, index=True)

    reaberto_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    justificativa_reabertura = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relacionamentos
    loja = relationship("Loja", back_populates="fechamentos")
    usuario = relationship("Usuario", foreign_keys=[usuario_id], back_populates="fechamentos")
    reaberto_por = relationship("Usuario", foreign_keys=[reaberto_por_id])
    itens = relationship("FechamentoItem", back_populates="fechamento", cascade="all, delete-orphan")


class FechamentoItem(Base):
    __tablename__ = "fechamento_itens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fechamento_id = Column(Integer, ForeignKey("fechamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)

    saldo_inicial = Column(Float, default=0.0, nullable=False)
    total_entradas = Column(Float, default=0.0, nullable=False)
    contagem_final = Column(Float, default=0.0, nullable=False)
    diferenca = Column(Float, default=0.0, nullable=False)
    observacao = Column(Text, nullable=True)

    # Relacionamentos
    fechamento = relationship("Fechamento", back_populates="itens")
    produto = relationship("Produto", back_populates="fechamento_itens")
