from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from db.neon_db import NeonDB, get_db
from models.user import User, UserRead, StatusBoletimRequest, AdminUserRequest, PerguntaCreate
from services.user_service import UserService
from services.mensagem_service import MensagemService
from routes.auth import get_current_active_user
from services.chat_service import ChatService
from models.user import AtualizarPerfilRequest



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

@router.put("/{user_id}/admin")
def update_admin(
    user_id: int,
    request: AdminUserRequest,
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza o status de admin do usuário (requer autenticação)"""
    result = user_service.alterar_status_admin(user_id, request.recebe_boletim, current_user.id, db)
    
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

@router.get("/tipo/{user_id}")
def tipo_usuario(
    user_id: int,
    db: NeonDB = Depends(get_db)
):
    """Retorna o tipo do usuário (requer autenticação)"""
    try:
        user = user_service.get_user(user_id, db)
        return user
    except Exception as e:
        print(f"[Rota /tipo/{{user_id}}] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar usuário")

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
        resposta_texto = result_resposta["mensagem"]["mensagem"]
        
        return {
            "success": True,
            "pergunta": result["pergunta"],
            "mensagem": resposta_texto
        }
    
    except Exception as e:
        print(f"[Rota enviar_pergunta] Erro ao processar: {e}")
        import traceback
        traceback.print_exc()
                
        return {
            "success": True,
            "pergunta": result["pergunta"],
            "mensagem": f"Erro ao processar: {str(e)}"
        }

@router.put(
    "/{user_id}/profile",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar perfil do usuário",
    description="Atualiza informações do perfil do usuário autenticado. O usuário só pode atualizar seu próprio perfil.",
    responses={
        200: {
            "description": "Perfil atualizado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "usuario@exemplo.com",
                        "username": "usuario",
                        "is_active": True,
                        "recebe_boletim": True
                    }
                }
            }
        },
        400: {
            "description": "Requisição inválida - nenhum campo para atualizar",
            "content": {
                "application/json": {
                    "example": {"detail": "Nenhum campo fornecido para atualização"}
                }
            }
        },
        403: {
            "description": "Acesso negado - tentativa de atualizar perfil de outro usuário",
            "content": {
                "application/json": {
                    "example": {"detail": "Você não tem permissão para atualizar o perfil de outro usuário"}
                }
            }
        },
        404: {
            "description": "Usuário não encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Usuário não encontrado"}
                }
            }
        }
    },
    tags=["usuários"]
)
def atualizar_perfil(
    user_id: int = Path(..., gt=0, description="ID do usuário a ser atualizado"),
    perfil: AtualizarPerfilRequest = Body(..., description="Dados do perfil a serem atualizados"),
    db: NeonDB = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserRead:
        
    # Validação de autorização - USUÁRIO SÓ PODE ATUALIZAR SEU PRÓPRIO PERFIL
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atualizar o perfil de outro usuário"
        )
    
    # Obter apenas campos fornecidos (não-None)
    dados_atualizacao = perfil.model_dump(exclude_unset=True)
    
    # Validar se pelo menos um campo foi fornecido
    if not dados_atualizacao:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo fornecido para atualização"
        )
    
    # Chamar serviço para atualizar o usuário
    try:
        result = user_service.atualizar_perfil(user_id, dados_atualizacao, db)
    except ValueError as e:
        # Captura erros de validação do serviço (ex: email duplicado)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log do erro real (usar logger em produção)
        print(f"[Rota atualizar_perfil] Erro inesperado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar perfil"
        )
    
    # Validar resultado do serviço
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", "Usuário não encontrado")
        )
    
    # Retornar dados atualizados
    user_atualizado = result["user"]
    
    return UserRead(
        id=user_atualizado["id"],
        email=user_atualizado["email"],
        username=user_atualizado["username"],
        is_active=user_atualizado.get("is_active", True),
        recebe_boletim=user_atualizado.get("recebe_boletim", False)
    )
