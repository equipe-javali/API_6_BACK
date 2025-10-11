from datetime import datetime
from typing import Optional

class ConversationModel:
    def __init__(self, 
                 id: Optional[int] = None,
                 user_id: int = None,
                 pergunta: str = None,
                 resposta: str = None,
                 timestamp: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.pergunta = pergunta
        self.resposta = resposta
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> dict:
        """Converte para dicionário para serialização"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_db_row(cls, row: tuple):
        """Cria instância a partir de linha do banco"""
        return cls(
            id=row[0],
            user_id=row[1],
            pergunta=row[2],
            resposta=row[3],
            timestamp=row[4]
        )