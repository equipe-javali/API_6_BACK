from db.neon_db import NeonDB  
from services.auth_service import get_password_hash  
from typing import List, Dict, Any, Optional

class MensagemService:
    """Serviço para gerenciar mensagens"""
    
    def get_mensagens(self, id_user: int, db: NeonDB) -> List[Dict[str, Any]]:
        """Lista um usuário específico"""
        mensagens = db.fetchall(
            "SELECT id, mensagem, ia, envio FROM mensagem WHERE id_usuario = %s",
            [id_user]
        )
        
        sorted_mensagens = sorted(
            [
                {
                    "id": mensagem[0],
                    "mensagem": mensagem[1],
                    "ia": mensagem[2],
                    "envio": mensagem[3]
                }
                for mensagem in mensagens
            ],
            key=lambda x: x["envio"],
            reverse=True
        )

        return sorted_mensagens
    