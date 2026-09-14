from datetime import datetime
from pydantic import BaseModel


class EntradaCreate(BaseModel):
    loja_id: int
    produto_id: int
    quantidade_recebida: float
    quantidade_esperada: float | None = None
    fornecedor: str | None = None
    nota_fiscal: str | None = None
    motivo_divergencia: str | None = None
    observacoes: str | None = None


class EntradaResponse(BaseModel):
    id: int
    loja_id: int
    produto_id: int
    produto_nome: str | None = None
    quantidade_recebida: float
    quantidade_esperada: float | None = None
    diferenca: float
    divergente: bool
    fornecedor: str | None = None
    nota_fiscal: str | None = None
    motivo_divergencia: str | None = None
    data_entrada: datetime

    class Config:
        from_attributes = True
