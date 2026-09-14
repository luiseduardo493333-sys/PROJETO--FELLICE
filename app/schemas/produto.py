from pydantic import BaseModel


class ProdutoBase(BaseModel):
    nome: str
    categoria: str
    unidade_medida: str = "UN"
    codigo_sku: str | None = None


class ProdutoCreate(ProdutoBase):
    estoque_minimo_padrao: float = 10.0
    estoque_maximo_padrao: float = 100.0


class ProdutoResponse(ProdutoBase):
    id: int
    ativo: bool

    class Config:
        from_attributes = True
