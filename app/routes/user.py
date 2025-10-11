from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel

from db.neon_db import NeonDB, get_db
from models.user import User, UserRead, StatusBoletimRequest
from services.user_service import UserService
from services.mensagem_service import MensagemService
from routes.auth import get_current_active_user

router = APIRouter(
    prefix="/users",
    tags=["usuários"],
    responses={404: {"description": "Não encontrado"}},
)

# Instância do serviço
user_service = UserService()
mensagem_service = MensagemService()

class CriarUsuario(BaseModel):
    email: str
    senha: str
    recebe_boletim: bool = True

@router.get("/", response_model=List[UserRead])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os usuários (requer autenticação)"""
    try:
        users = user_service.get_users(skip, limit, db)
               
        return [
            UserRead(
                id=user["id"],
                email=user["email"],
                username=user["username"],
                is_active=True,
                recebe_boletim=user.get("recebe_boletim", False)
            )
            for user in users
        ]
    except Exception as e:
        print(f"Erro ao buscar usuários: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuários: {str(e)}"
        )

@router.get("/{user_id}/status-boletim")
def get_status_boletim(
    user_id: int, 
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Consulta o status de recebimento de boletim de um usuário (requer autenticação)"""
    result = user_service.get_status_boletim(user_id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result

@router.put("/{user_id}/status")
def update_status(
    user_id: int,
    request: StatusBoletimRequest,
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza o status de recebimento de boletim (requer autenticação)"""
    result = user_service.alterar_status_boletim(user_id, request.recebe_boletim, current_user.id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
        
    return result

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Exclui um usuário (requer autenticação)"""
    result = user_service.delete_user(user_id, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
        
    return result

@router.post("/usuario")
def criar_usuario(request: CriarUsuario):
    try:
        return user_service.criar_user(
            request.email,
            request.senha,
            request.recebe_boletim
        )
    except Exception as e:
        print(f"[Rota /usuario] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar usuário")

@router.get("/mensagens/{user_id}")
def historico_mensagens(
    user_id: int,
    db: NeonDB = Depends(get_db)
):
    """Lista o histórico de mensagens de um usuário (requer autenticação)"""
    try:
        mensagens = mensagem_service.get_mensagens(user_id, db)
        return mensagens
    except Exception as e:
        print(f"[Rota /mensagens/{{user_id}}] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar usuário")
