from typing import Dict, Any, List
from db.neon_db import NeonDB
from services.agent_service import AgentService
from services.context_service import ContextService
from services.QueryAnalyzer import QueryAnalyzer
from services.user_service import UserService

class ChatService:
    """Serviço que integra agente de IA, contexto de dados e banco de dados para responder perguntas"""

    def __init__(self):
        self.agent = AgentService()
        self.context_service = ContextService()
        self.query_analyzer = QueryAnalyzer()
        self.user_service = UserService()

    def processar_pergunta(self, user_id: int, pergunta: str, db: NeonDB) -> Dict[str, Any]:
        print(f"[Chat] Processando pergunta: '{pergunta}'")
        try:
            # Analisar a pergunta
            analise = self.query_analyzer.analyze_query(pergunta)
            if not analise:
                # Se não há análise, assumir foco padrão para perguntas ambíguas
                analise = {"focus": ["estoque", "faturamento"], "type": "general", "filters": {}, "complexity_score": 0, "requires_detailed_data": False}
            if not analise.get("focus"):
                analise["focus"] = ["estoque", "faturamento"]  # Fallback para ambos se foco vazio

            print(f"[Chat] Análise obtida: {analise}")

            # Salvar a pergunta no banco
            pergunta_result = self.user_service.enviar_pergunta(user_id, pergunta, False, db)
            if not pergunta_result["success"]:
                return {"success": False, "message": "Erro ao salvar pergunta"}

            # Gerar contexto base
            contexto = self.context_service.get_combined_context(user_id, query_hint=pergunta)
            print(f"[Chat] Contexto gerado: {len(contexto)} caracteres")

            # Processar resposta com AgentService
            resposta = self.agent.process_input(pergunta, contexto)
            print(f"[Chat] Resposta gerada: '{resposta}'")

            # Salvar a resposta no banco
            resposta_result = self.user_service.enviar_pergunta(user_id, resposta, True, db)
            if not resposta_result["success"]:
                print("[Chat] Erro ao salvar resposta IA")

            saved_id = resposta_result.get("pergunta", {}).get("id") if resposta_result["success"] else None
            mensagem = {
                "id": saved_id,
                "id_usuario": user_id,
                "mensagem": resposta,
                "ia": True,
                "envio": "agora"
            }
            return {
                "success": True,
                "mensagem": mensagem
            }
        except Exception as e:
            print(f"[Chat] Erro no processamento: {e}")
            resposta = "Desculpe, ocorreu um erro ao processar sua pergunta."
            return {
                "success": False,
                "mensagem": {
                    "id_usuario": user_id,
                    "mensagem": resposta,
                    "ia": True,
                    "envio": "agora"
                }
            }