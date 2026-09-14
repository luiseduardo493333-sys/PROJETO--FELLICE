from pydantic import BaseModel, EmailStr


class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    role: str
    loja_id: int | None = None


class UsuarioCreate(UsuarioBase):
    senha: str


class UsuarioTransfer(BaseModel):
    nova_loja_id: int


class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    loja_nome: str | None = None

    class Config:
        from_attributes = True
