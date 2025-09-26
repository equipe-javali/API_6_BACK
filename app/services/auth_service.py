import os
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

# Importar NeonDB para acesso ao banco
from db.neon_db import NeonDB, get_db
from models.user import User

load_dotenv()

# Configurações de segurança
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(email: str, db: NeonDB = None) -> Optional[User]:
    """Busca um usuário no banco de dados pelo e-mail"""
    if not db:
        db = NeonDB()  
    
    try:
        # Removida coluna username da consulta
        user_row = db.fetchone("SELECT id, email, senha, recebe_boletim FROM usuario WHERE email = %s", [email])
        if not user_row:
            return None
        
        # Criamos username a partir do email
        email_parts = user_row[1].split('@')
        username = email_parts[0] if email_parts else user_row[1]
        
        # Mapeia os resultados do banco para o modelo User
        user_dict = {
            "id": user_row[0],
            "email": user_row[1],
            "username": username,  # Gerado a partir do email
            "hashed_password": user_row[2],  
            "is_active": True  
        }
        return User(**user_dict)
    finally:
        if not db:
            db.__exit__(None, None, None)

def authenticate_user(email: str, password: str, db: NeonDB = None) -> Optional[User]:
    """Autentica um usuário verificando email e senha no banco"""
    user = get_user(email, db)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() 
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: NeonDB = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(email, db)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user