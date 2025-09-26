from pydantic import BaseModel
from ..db.neon_db import NeonDB

class Relatorio(BaseModel):
    titulo: str
    conteudo: str

def get_usuarios_boletim() -> list[dict]:
    
    sql = "SELECT id, email FROM usuario WHERE recebe_boletim = TRUE"
    with NeonDB() as db:
        rows = db.query(sql)
    
    # Converte o resultado em lista de dicts
    usuarios = [{"id": r[0], "email": r[1]} for r in rows]
    return usuarios