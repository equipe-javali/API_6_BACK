from db.neon_db import NeonDB  
from services.auth_service import get_password_hash  
from typing import List, Dict, Any, Optional
import traceback

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

    def enviar_pergunta(self, id_usuario: int, mensagem: str, ia: bool, db: NeonDB) -> Dict[str, Any]:
        """
        Persiste uma pergunta no banco e retorna o registro criado.
        """
        try:
            try:
                test = db.fetchone("SELECT 1", None)
                print(f"[UserService.enviar_pergunta] Test DB SELECT 1 retornou: {test}")
            except Exception as e_test:
                print(f"[UserService.enviar_pergunta] Falha no teste DB: {e_test}")

            print("[UserService.enviar_pergunta] Tabela 'mensagem' assumida existente; prosseguindo com INSERT")
            print("[UserService.enviar_pergunta] Executando INSERT na tabela mensagem (sem id)...")
            
            # Trunca a mensagem para 255 caracteres para evitar erro de banco
            mensagem_truncada = mensagem[:255] if len(mensagem) > 255 else mensagem
            
            row = db.fetchone(
                "INSERT INTO mensagem (id_usuario, mensagem, ia, envio) VALUES (%s, %s, %s, NOW()) RETURNING id, envio",
                [id_usuario, mensagem_truncada, ia]
            )
            print(f"[UserService.enviar_pergunta] Resultado do INSERT (row): {row}")
            db.commit()

            if not row:
                print("[UserService.enviar_pergunta] INSERT não retornou row")
                return {"success": False, "message": "Falha ao inserir pergunta"}

            print(f"[UserService.enviar_pergunta] Pergunta salva com id={row[0]}, envio={row[1]}")
            return {
                "success": True,
                "pergunta": {
                    "id": row[0],
                    "id_usuario": id_usuario,
                    "mensagem": mensagem_truncada,
                    "ia": ia,
                    "envio": row[1]
                }
            }
        except Exception as e:
            # Log completo com traceback e retorna erro
            print(f"[UserService.enviar_pergunta] Erro ao salvar pergunta: {e}")
            traceback.print_exc()
            return {"success": False, "message": str(e)}

    
    
    

    