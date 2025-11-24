from pydantic import BaseModel
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    hashed_password: str
    admin: bool

    class Config:
        from_attributes = True 

class UserRead(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    recebe_boletim: bool
    admin: bool
    
    class Config:
        from_attributes = True
        
class StatusBoletimRequest(BaseModel):
    recebe_boletim: bool

class AdminUserRequest(BaseModel):
    admin: bool

# Modelos para perguntas (chat)
class PerguntaCreate(BaseModel):
    id_usuario: int
    mensagem: str
    ia: bool


class Pergunta(PerguntaCreate):
    id: int
    envio: datetime

class PerguntaComResposta(BaseModel):
    """Modelo para retornar pergunta + resposta"""
    success: bool
    pergunta: Pergunta
    resposta: str

class AtualizarPerfilRequest(BaseModel):
    """Schema para atualização de perfil do usuário."""
    email: Optional[EmailStr] = Field(None, description="Novo email do usuário")
    senha: Optional[str] = Field(None, min_length=6, description="Nova senha do usuário")
    recebe_boletim: Optional[bool] = Field(None, description="Preferência de recebimento de boletim")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "novoemail@exemplo.com",
                "senha": "nova_senha123",
                "recebe_boletim": True
            }
        }
