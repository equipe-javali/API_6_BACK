from ..db.neon_db import NeonDB

class UsuarioService:
    def alterar_status_boletim(self, user_id: int, recebe_boletim: bool, admin_user_id: int) -> dict:
        """
        Altera o status de recebimento de boletim de um usuário.
        Apenas administradores podem usar esta função.
        """
        with NeonDB() as db:
            # Verificar se o usuário administrador existe
            admin_query = "SELECT id FROM usuario WHERE id = %s"
            admin_result = db.fetchone(admin_query, [admin_user_id])
            if not admin_result:
                return {
                    "success": False,
                    "message": "Usuário administrador não encontrado"
                }
            
            # Verificar se o usuário alvo existe
            user_query = "SELECT id, email, recebe_boletim FROM usuario WHERE id = %s"
            user_result = db.fetchone(user_query, [user_id])
            if not user_result:
                return {
                    "success": False,
                    "message": "Usuário não encontrado"
                }
            
            # Atualizar o status do boletim
            update_query = "UPDATE usuario SET recebe_boletim = %s WHERE id = %s"
            db.execute(update_query, [recebe_boletim, user_id])
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

    def get_status_boletim(self, user_id: int) -> dict:
        """
        Consulta o status atual de recebimento de boletim de um usuário.
        """
        with NeonDB() as db:
            query = "SELECT id, email, recebe_boletim FROM usuario WHERE id = %s"
            result = db.fetchone(query, [user_id])
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

    def criar_usuario(self, email: str, senha: str, recebe_boletim: bool = True) -> dict:
        """
        Cria um novo usuário para teste.
        """
        with NeonDB() as db:
            existing = db.fetchone("SELECT id FROM usuario WHERE email = %s", [email])
            if existing:
                return {"success": False,"message": "Email já cadastrado"}
            result = db.fetchone(
                "INSERT INTO usuario (email, senha, recebe_boletim) VALUES (%s, %s, %s) RETURNING id",
                [email, senha, recebe_boletim]
            )
            db.commit()
            return {
                "success": True,
                "message": "Usuário criado com sucesso",
                "usuario": {
                    "id": result[0],
                    "email": email,
                    "recebe_boletim": recebe_boletim
                }
            }

    def listar_usuarios(self) -> dict:
        """
        Lista todos os usuários cadastrados.
        """
        with NeonDB() as db:
            query = "SELECT id, email, recebe_boletim FROM usuario ORDER BY id"
            results = db.query(query)
            usuarios = [
                {"id": row[0], "email": row[1], "recebe_boletim": row[2]}
                for row in results
            ]
            return {
                "success": True,
                "usuarios": usuarios,
                "total": len(usuarios)
            }