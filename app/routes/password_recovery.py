from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from services.password_recovery_service import PasswordRecoveryService

router = APIRouter(prefix="/password", tags=["Password Recovery"])

class RecoveryRequest(BaseModel):
    email: EmailStr

@router.post("/recover")
def recover_password(request: RecoveryRequest):
    """
    Endpoint para recuperação de senha.
    Envia uma senha temporária para o e-mail do usuário.
    """
    service = PasswordRecoveryService()
    
    try:
        success, message = service.recover(request.email)
        
        if not success:
            raise HTTPException(status_code=404, detail=message)
        
        return {
            "success": True,
            "message": message,
            "detail": "Verifique seu e-mail para a nova senha temporária"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao recuperar senha: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao processar recuperação de senha"
        )