from db.neon_db import NeonDB  
from services.auth_service import get_password_hash  
from typing import List, Dict, Any, Optional

class UserService:
    """Serviço para gerenciar usuários"""
        
    def get_user(self, id: int, db: NeonDB) -> List[Dict[str, Any]]:
        """Lista usuários com paginação"""
        user = db.fetchall(
            "SELECT id, email, recebe_boletim, admin FROM usuario WHERE id = %s",
            [id]
        )[0]
        
        return {
            "id": user[0],
            "email": user[1], 
            "username": user[1].split('@')[0],
            "recebe_boletim": user[2],
            "admin": bool(user[3])
        }
    
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
    
    def delete_user(self, user_id: int, db: NeonDB) -> Dict[str, Any]:
        """
        Exclui um usuário do sistema.
        """
        # Verificar se o usuário existe
        user_result = db.fetchone("SELECT id, email FROM usuario WHERE id = %s", [user_id])
        if not user_result:
            return {
                "success": False,
                "message": "Usuário não encontrado"
            }
        
        # Excluir o usuário
        db.execute("DELETE FROM usuario WHERE id = %s", [user_id])
        db.commit()
        
        return {
            "success": True,
            "message": "Usuário excluído com sucesso",
            "usuario_excluido": {
                "id": user_result[0],
                "email": user_result[1]
            }
        }
    
    def criar_user(self, email: str, senha: str, recebe_boletim: bool = True) -> dict:
        """
        Cria um novo usuário no sistema, salvando a senha criptografada.
        """
        with NeonDB() as db:
            existing = db.fetchone("SELECT id FROM usuario WHERE email = %s", [email])
            if existing:
                return {"success": False, "message": "Esse e-mail já foi cadastrado!"}
            
            senha_hash = get_password_hash(senha)  
            
            result = db.fetchone(
                "INSERT INTO usuario (email, senha, recebe_boletim) VALUES (%s, %s, %s) RETURNING id",
                [email, senha_hash, recebe_boletim]
            )
            db.commit()
            return {
                "success": True,
                "message": "Usuário criado com sucesso!",
                "usuario": {
                    "id": result[0],
                    "email": email,
                    "recebe_boletim": recebe_boletim
                }
            }

    
    
    

    