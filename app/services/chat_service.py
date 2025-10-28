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
            # Verificar se é uma saudação simples
            if self._is_saudacao_simples(pergunta):
                resposta_saudacao = self._gerar_resposta_saudacao(pergunta)
                
                # Salvar a pergunta no banco
                pergunta_result = self.user_service.enviar_pergunta(user_id, pergunta, False, db)
                if not pergunta_result["success"]:
                    return {"success": False, "message": "Erro ao salvar pergunta"}

                # Salvar a resposta no banco
                resposta_result = self.user_service.enviar_pergunta(user_id, resposta_saudacao, True, db)
                if not resposta_result["success"]:
                    print("[Chat] Erro ao salvar resposta de saudação")

                saved_id = resposta_result.get("pergunta", {}).get("id") if resposta_result["success"] else None
                mensagem = {
                    "id": saved_id,
                    "id_usuario": user_id,
                    "mensagem": resposta_saudacao,
                    "ia": True,
                    "envio": "agora"
                }
                return {
                    "success": True,
                    "mensagem": mensagem
                }

            # Analisar a pergunta
            analise = self.query_analyzer.analyze_query(pergunta)
            if not analise:
                # Se não há análise, considerar pergunta fora do escopo (não chamar IA)
                print("[Chat] Pergunta fora do escopo detectada pelo QueryAnalyzer. Respondendo com recusa padrão.")

                # Salvar a pergunta no banco
                pergunta_result = self.user_service.enviar_pergunta(user_id, pergunta, False, db)
                if not pergunta_result["success"]:
                    return {"success": False, "message": "Erro ao salvar pergunta"}

                # Mensagem de recusa — não inventar respostas para tópicos fora do domínio
                recusa = (
                    "Desculpe, não tenho acesso a dados ou serviços para responder a essa pergunta. "
                    "Posso ajudar com análises relacionadas a estoque ou faturamento."
                )

                resposta_result = self.user_service.enviar_pergunta(user_id, recusa, True, db)
                if not resposta_result["success"]:
                    print("[Chat] Erro ao salvar resposta de recusa")

                saved_id = resposta_result.get("pergunta", {}).get("id") if resposta_result["success"] else None
                mensagem = {
                    "id": saved_id,
                    "id_usuario": user_id,
                    "mensagem": recusa,
                    "ia": True,
                    "envio": "agora"
                }
                return {
                    "success": True,
                    "mensagem": mensagem
                }
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
            resposta = self.agent.process_input(pergunta, contexto, analise)
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

    def _is_saudacao_simples(self, pergunta: str) -> bool:
        """Verifica se a pergunta é uma saudação simples que não requer análise de dados"""
        pergunta_lower = pergunta.lower().strip()
        
        # Lista de saudações comuns em português
        saudacoes = [
            'oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 
            'boa madrugada', 'bom tarde', 'bom noite', 'bom madrugada',
            'oi tudo bem', 'ola tudo bem', 'oi como vai', 'ola como vai',
            'tudo bem', 'como vai', 'como está', 'e aí', 'eae', 'salve',
            'opa', 'ei', 'psiu', 'alô', 'hello', 'hi', 'hey'
        ]
        
        # Verificar se a pergunta é exatamente uma saudação ou contém apenas uma saudação
        for saudacao in saudacoes:
            if pergunta_lower == saudacao or pergunta_lower.startswith(saudacao + ' ') or pergunta_lower.endswith(' ' + saudacao):
                return True
        
        # Verificar se é uma saudação simples com pontuação
        if pergunta_lower in ['oi!', 'olá!', 'ola!', 'oi?', 'olá?', 'ola?', 'oi.', 'olá.', 'ola.']:
            return True
            
        # Verificar se é uma saudação com variações mínimas (máximo 2 palavras extras)
        palavras = pergunta_lower.split()
        if len(palavras) <= 3:
            saudacao_encontrada = False
            for palavra in palavras:
                if any(saudacao in palavra for saudacao in saudacoes):
                    saudacao_encontrada = True
                    break
            if saudacao_encontrada:
                return True
        
        return False

    def _gerar_resposta_saudacao(self, pergunta: str) -> str:
        """Gera uma resposta apropriada para saudações"""
        pergunta_lower = pergunta.lower().strip()
        
        # Respostas baseadas no tipo de saudação
        if 'bom dia' in pergunta_lower or 'bomdia' in pergunta_lower:
            return "Bom dia! Sou seu assistente especializado em análise de dados corporativos. Como posso ajudar você hoje?"
            
        elif 'boa tarde' in pergunta_lower or 'boatarde' in pergunta_lower:
            return "Boa tarde! Sou seu assistente especializado em análise de dados corporativos. Como posso ajudar você hoje?"
            
        elif 'boa noite' in pergunta_lower or 'boanoite' in pergunta_lower:
            return "Boa noite! Sou seu assistente especializado em análise de dados corporativos. Como posso ajudar você hoje?"
            
        elif 'boa madrugada' in pergunta_lower or 'boamadrugada' in pergunta_lower:
            return "Boa madrugada! Sou seu assistente especializado em análise de dados corporativos. Como posso ajudar você hoje?"
        
        # Saudação genérica para outros casos
        else:
            return "Olá! Sou seu assistente especializado em análise de dados corporativos. Como posso ajudar você hoje?"