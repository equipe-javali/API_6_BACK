from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    hashed_password: str

    class Config:
        from_attributes = True 

class UserRead(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool

    class Config:
        from_attributes = True
        
class StatusBoletimRequest(BaseModel):
    recebe_boletim: bool