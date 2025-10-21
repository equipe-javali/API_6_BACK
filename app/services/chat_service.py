from typing import Dict, Any
from db.neon_db import NeonDB
from models.conversation_model import ConversationModel
from services.agent_service import AgentService
from services.context_service import ContextService

class ChatService:
    """Serviço que integra agente de IA, contexto de dados e banco de dados para responder perguntas"""
    
    def __init__(self):
        self.agent = AgentService()
        self.context_service = ContextService()
    
    def processar_pergunta(self, user_id: int, pergunta: str, db: NeonDB) -> Dict[str, Any]:
        """
        Processa uma pergunta do usuário usando o agente de IA e contexto do banco de dados
        
        Args:
            user_id: ID do usuário que fez a pergunta
            pergunta: Texto da pergunta
            db: Conexão com o banco de dados
            
        Returns:
            Dicionário com sucesso, pergunta e resposta
        """
        # 1. Obter contexto relevante do banco de dados
        contexto = self.context_service.get_combined_context(user_id, query_hint=pergunta)
        
        # 2. Processar a pergunta usando o agente e o contexto
        resposta = self.agent.process_input(pergunta, contexto)
        
        # 3. Salvar a resposta no banco de dados
        conversation = ConversationModel(
            user_id=user_id,
            pergunta=pergunta,
            resposta=resposta
        )
        
        # 4. Salvar no banco
        saved_id = self._salvar_resposta(user_id, pergunta, resposta, db)
        conversation.id = saved_id
        
        return {
            "success": True,
            "conversation": conversation.to_dict()
        }
    
    def _salvar_resposta(self, user_id: int, pergunta: str, resposta: str, db: NeonDB) -> int:
        """Salva a pergunta e resposta no banco de dados"""
        
        # Inserir a resposta na tabela conversation (ou criar essa tabela se não existir)
        try:
            # Verificar se a tabela conversation existe
            table_exists = db.fetchone(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversation'
                )
                """
            )
            
            if not table_exists or not table_exists[0]:
                # Criar a tabela se não existir
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        pergunta TEXT NOT NULL,
                        resposta TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
                db.commit()
                print("Tabela 'conversation' criada")
            
            # Inserir a resposta
            result = db.fetchone(
                """
                INSERT INTO conversation (user_id, pergunta, resposta, timestamp)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
                """,
                [user_id, pergunta, resposta]
            )
            
            db.commit()
            return result[0] if result else None
            
        except Exception as e:
            print(f"Erro ao salvar resposta: {e}")
            # Tentar salvar na tabela mensagem como fallback
            try:
                # Inserir como mensagem do sistema (ia=True)
                result = db.fetchone(
                    """
                    INSERT INTO mensagem (id_usuario, mensagem, ia, envio)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                    """,
                    [user_id, resposta, True]
                )
                
                db.commit()
                return result[0] if result else None
            
            except Exception as inner_e:
                print(f"Erro ao salvar como mensagem: {inner_e}")
                return None