from pydantic import BaseModel


class LojaBase(BaseModel):
    nome: str
    codigo: str
    endereco: str | None = None
    telefone: str | None = None


class LojaCreate(LojaBase):
    pass


class LojaResponse(LojaBase):
    id: int
    ativa: bool

    class Config:
        from_attributes = True
