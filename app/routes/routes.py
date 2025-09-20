from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.UsuarioService import UsuarioService

router = APIRouter()
usuario_service = UsuarioService()

class AlterarStatusBoletimRequest(BaseModel):
    user_id: int
    recebe_boletim: bool
    admin_user_id: int

class CriarUsuarioRequest(BaseModel):
    email: str
    senha: str
    recebe_boletim: bool = True

@router.put("/usuario/status-boletim")
def alterar_status_boletim(request: AlterarStatusBoletimRequest):
    """
    Altera o status de recebimento de boletim de um usuário.
    Apenas administradores podem usar esta rota.
    """
    return usuario_service.alterar_status_boletim(
        request.user_id, 
        request.recebe_boletim, 
        request.admin_user_id
    )

@router.get("/usuario/{user_id}/status-boletim")
def get_status_boletim(user_id: int):
    """
    Consulta o status atual de recebimento de boletim de um usuário.
    """
    return usuario_service.get_status_boletim(user_id)

@router.post("/usuario")
def criar_usuario(request: CriarUsuarioRequest):
    try:
        return usuario_service.criar_usuario(
            request.email,
            request.senha,
            request.recebe_boletim
        )
    except Exception as e:
        print(f"[Rota /usuario] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar usuário")

@router.get("/usuarios")
def listar_usuarios():
    """
    Lista todos os usuários cadastrados.
    """
    return usuario_service.listar_usuarios()