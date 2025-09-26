from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from passlib.context import CryptContext

from db.neon_db import get_db, NeonDB
from models.user import User, UserCreate, UserRead
from routes.auth import get_current_active_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Configuração do hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)



@router.get("/read", response_model=List[UserRead])  # Mude para UserRead
def read_users(skip: int = 0, limit: int = 10, db: NeonDB = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    try:
        # Consulta ajustada para incluir username (gerado do email)
        users = db.fetchall("SELECT id, email, recebe_boletim FROM usuario ORDER BY id OFFSET %s LIMIT %s", [skip, limit])
        
        # Mapeie para UserRead
        user_list = []
        for row in users:
            username = row[1].split('@')[0]  # Gera username do email
            user_dict = {
                "id": row[0],
                "email": row[1],
                "username": username,
                "is_active": True  # Assumindo que todos são ativos
            }
            user_list.append(UserRead(**user_dict))
        
        return user_list
    except Exception as e:
        print(f"Erro ao buscar usuários: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuários: {str(e)}"
        )