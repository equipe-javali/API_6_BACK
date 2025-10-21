from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from datetime import datetime
from db.neon_db import NeonDB, get_db
from models.user import PerguntaComResposta, User, UserRead, StatusBoletimRequest, PerguntaCreate, Pergunta
from services.user_service import UserService
from services.mensagem_service import MensagemService
from routes.auth import get_current_active_user
from services.chat_service import ChatService



router = APIRouter(
    prefix="/users",
    tags=["usuários"],
    responses={404: {"description": "Não encontrado"}},
)

# Instância do serviço
user_service = UserService()
chat_service = ChatService()




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


# Rota para enviar pergunta
@router.post("/enviar-pergunta")
def enviar_pergunta(
    pergunta: PerguntaCreate,
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    
    print(f"[Rota enviar_pergunta] Recebido request para id_usuario={pergunta.id_usuario}")
    # Apenas permite que o usuário autenticado envie pergunta em seu próprio id, ou admin poderia ser implementado
    if current_user.id != pergunta.id_usuario:
        print(f"[Rota enviar_pergunta] Falha na validação de usuário: current_user.id={current_user.id} != pergunta.id_usuario={pergunta.id_usuario}")
        raise HTTPException(status_code=403, detail="Não autorizado a enviar pergunta para outro usuário")

    
    result = user_service.enviar_pergunta(pergunta.id_usuario, pergunta.mensagem, False, db)
    print(f"[Rota enviar_pergunta] Resultado do serviço: {result}")

    if not result.get("success"):
        print(f"[Rota enviar_pergunta] Serviço retornou erro: {result.get('message')}")
        raise HTTPException(status_code=500, detail=result.get("message", "Erro ao salvar pergunta"))

    p = result["pergunta"]
    print(f"[Rota enviar_pergunta] Retornando Pergunta id={p['id']}")
    # Processar com IA
    try:
        print(f"[Rota enviar_pergunta] Processando pergunta com IA...")
        result_resposta = chat_service.processar_pergunta(
            pergunta.id_usuario,
            pergunta.mensagem,
            db
        )
        
        if not result_resposta.get("success"):
            print(f"[Rota enviar_pergunta] Erro ao processar: {result_resposta.get('error')}")
            raise Exception(result_resposta.get("error", "Erro ao processar pergunta"))
        
        print(f"[Rota enviar_pergunta] Resposta gerada com sucesso")
        
        # 3. Retornar resultado completo (pergunta + resposta)
        resposta_texto = result_resposta["conversation"]["resposta"]
        
        return {
            "success": True,
            "pergunta": result["pergunta"],
            "mensagem": resposta_texto
        }
    
    except Exception as e:
        print(f"[Rota enviar_pergunta] Erro ao processar: {e}")
        import traceback
        traceback.print_exc()
        
        # ✨ Fallback: retorna a pergunta salva mesmo se IA falhar
        # Assim o usuário não perde a pergunta
        return {
            "success": True,
            "pergunta": result["pergunta"],
            "mensagem": f"Erro ao processar: {str(e)}"
        }
