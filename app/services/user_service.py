from db.neon_db import NeonDB  
from services.auth_service import get_password_hash  
from typing import List, Dict, Any, Optional

class UserService:
    """Serviço para gerenciar usuários"""
        
    
    def get_users(self, skip: int, limit: int, db: NeonDB) -> List[Dict[str, Any]]:
        """Lista usuários com paginação"""
        users = db.fetchall(
            "SELECT id, email, recebe_boletim FROM usuario ORDER BY id OFFSET %s LIMIT %s",
            [skip, limit]
        )
               
        return [
            {
                "id": user[0],
                "email": user[1], 
                "username": user[1].split('@')[0],
                "recebe_boletim": user[2]
            }
            for user in users
        ]
    
    def alterar_status_boletim(self, user_id: int, recebe_boletim: bool, admin_user_id: int, db: NeonDB) -> Dict[str, Any]:
        """
        Altera o status de recebimento de boletim de um usuário.
        Apenas administradores podem usar esta função.
        """
        # Verificar se o usuário administrador existe
        admin_result = db.fetchone("SELECT id FROM usuario WHERE id = %s", [admin_user_id])
        if not admin_result:
            return {
                "success": False,
                "message": "Usuário administrador não encontrado"
            }
        
        # Verificar se o usuário alvo existe
        user_result = db.fetchone("SELECT id, email, recebe_boletim FROM usuario WHERE id = %s", [user_id])
        if not user_result:
            return {
                "success": False,
                "message": "Usuário não encontrado"
            }
        
        # Atualizar o status do boletim
        db.execute("UPDATE usuario SET recebe_boletim = %s WHERE id = %s", [recebe_boletim, user_id])
        db.commit()

        return {
            "success": True,
            "message": f"Status do boletim alterado com sucesso para {recebe_boletim}",
            "usuario": {
                "id": user_result[0],
                "email": user_result[1],
                "recebe_boletim_anterior": user_result[2],
                "recebe_boletim_novo": recebe_boletim
            }
        }

    def get_status_boletim(self, user_id: int, db: NeonDB) -> Dict[str, Any]:
        """
        Consulta o status atual de recebimento de boletim de um usuário.
        """
        result = db.fetchone("SELECT id, email, recebe_boletim FROM usuario WHERE id = %s", [user_id])
        if not result:
            return {
                "success": False,
                "message": "Usuário não encontrado"
            }
        
        return {
            "success": True,
            "usuario": {
                "id": result[0],
                "email": result[1],
                "recebe_boletim": result[2]
            }
        }

    