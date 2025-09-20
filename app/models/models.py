from pydantic import BaseModel

class Relatorio(BaseModel):
    titulo: str
    conteudo: str
