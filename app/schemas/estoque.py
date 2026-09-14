from pydantic import BaseModel


class EstoqueItemResponse(BaseModel):
    produto_id: int
    nome: str
    categoria: str
    unidade_medida: str
    saldo_atual: float
    estoque_minimo: float
    estoque_maximo: float
    status: str

    class Config:
        from_attributes = True


class EstoqueLojaResponse(BaseModel):
    loja_id: int
    loja_nome: str
    total_itens: int
    itens: list[EstoqueItemResponse]
