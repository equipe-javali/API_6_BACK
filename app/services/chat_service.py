from typing import Dict, Any, List
from db.neon_db import NeonDB
from services.agent_service import AgentService
from services.context_service import ContextService
from services.QueryAnalyzer import QueryAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ChatService:
    """Serviço que integra agente de IA, contexto de dados e banco de dados para responder perguntas"""

    def __init__(self):
        self.agent = AgentService()
        self.context_service = ContextService()
        self.query_analyzer = QueryAnalyzer()

    def processar_pergunta(self, user_id: int, pergunta: str, db: NeonDB, usar_knn: bool = False) -> Dict[str, Any]:
        print(f"[Chat] Processando pergunta: '{pergunta}'")
        try:
            db.execute("ROLLBACK")
            analise = self.query_analyzer.analyze_query(pergunta)
            print(f"[Chat] Análise obtida: {analise}")

            historico_usuario = []
            perguntas_similares = []
            if usar_knn:
                historico_usuario = self._buscar_historico_usuario(user_id, db, limite=20)
                perguntas_similares = self._knn_buscar_similares(pergunta, historico_usuario, k=3)

            contexto = self._obter_contexto_base(user_id, pergunta, analise)
            print(f"[Chat] Contexto base: {len(contexto)} caracteres")

            dados_especificos = self._buscar_dados_especificos(pergunta, db)

            contexto_enriquecido = contexto
            if usar_knn and perguntas_similares:
                contexto_enriquecido = self._enriquecer_contexto(contexto, perguntas_similares)

            prompt_final = self._criar_prompt_melhorado(
                pergunta,
                contexto_enriquecido,
                dados_especificos,
                analise,
                tem_historico=len(perguntas_similares) > 0
            )

            print(f"[Chat] Prompt final tem {len(prompt_final)} caracteres")
            print(f"[Chat] PROMPT COMPLETO:\n{prompt_final}")
            print(f"[Chat] ===== FIM DO PROMPT =====")

            resposta = self.agent.process_input(pergunta, prompt_final, analise=analise)
            print(f"[Chat] Resposta gerada: '{resposta}'")

            saved_id = self._salvar_resposta(user_id, pergunta, resposta, db)
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
            try:
                db.execute("ROLLBACK")
            except:
                pass
            resposta = f"Desculpe, não consegui processar sua pergunta no momento."
            return {
                "success": False,
                "mensagem": {
                    "id_usuario": user_id,
                    "mensagem": resposta,
                    "ia": True,
                    "envio": "agora"
                }
            }

    def _buscar_historico_usuario(self, user_id: int, db: NeonDB, limite: int = 20) -> List[Dict]:
        try:
            db.execute("ROLLBACK")
            resultados = db.fetchall(
                """
                WITH pares AS (
                    SELECT 
                        m1.id as pergunta_id,
                        m1.mensagem as pergunta,
                        m1.envio as timestamp,
                        (
                            SELECT m2.mensagem 
                            FROM mensagem m2 
                            WHERE m2.id_usuario = m1.id_usuario 
                            AND m2.ia = TRUE 
                            AND m2.envio > m1.envio
                            ORDER BY m2.envio ASC
                            LIMIT 1
                        ) as resposta
                    FROM mensagem m1
                    WHERE m1.id_usuario = %s 
                    AND m1.ia = FALSE
                    ORDER BY m1.envio DESC
                    LIMIT %s
                )
                SELECT pergunta, resposta, timestamp FROM pares
                WHERE resposta IS NOT NULL
                """,
                [user_id, limite * 2]
            )
            if resultados:
                historico = [{"pergunta": row[0], "resposta": row[1], "timestamp": str(row[2])} for row in resultados if row[1] is not None]
                historico = historico[:limite]
                print(f"[KNN] Histórico do usuário {user_id}: {len(historico)} pares pergunta-resposta encontrados")
                return historico
            print(f"[KNN] Nenhum histórico encontrado para usuário {user_id}")
            return []
        except Exception as e:
            print(f"[KNN] Erro ao buscar histórico: {e}")
            try:
                db.execute("ROLLBACK")
            except:
                pass
            return []

    def _knn_buscar_similares(self, pergunta: str, historico: List[Dict], k: int = 3) -> List[Dict]:
        if not historico or len(historico) < 2:
            return []
        try:
            perguntas_historico = [h["pergunta"] for h in historico]
            todos_documentos = [pergunta] + perguntas_historico
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(todos_documentos)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
            top_indices = np.argsort(similarities)[::-1][:k]
            frases_erro = [
                "desculpe", "erro", "não consegui", "ocorreu um erro", 
                "falha", "tente novamente", "tente ser mais específico"
            ]
            similares = []
            for idx in top_indices:
                sim_score = float(similarities[idx])
                if sim_score > 0.3:
                    resposta_lower = historico[idx]["resposta"].lower()
                    if not any(erro in resposta_lower for erro in frases_erro):
                        similares.append({
                            **historico[idx],
                            "similaridade": sim_score
                        })
                        print(f"[KNN DEBUG] Pergunta similar: '{perguntas_historico[idx]}' - Similaridade: {sim_score:.2f}")
            print(f"[KNN] Encontradas {len(similares)} perguntas similares após filtro")
            return similares
        except Exception as e:
            print(f"[KNN] Erro ao aplicar KNN: {e}")
            return []

    def _buscar_dados_especificos(self, pergunta: str, db: NeonDB) -> str:
        """Busca dados específicos usando PLN para extrair filtros e formatar respostas naturais"""
        dados = ""
        pergunta_lower = pergunta.lower()
        
        # Usar QueryAnalyzer para extrair filtros com PLN
        analise = self.query_analyzer.analyze_query(pergunta)
        filters = analise.get("filters", {})
        
        try:
            db.execute("ROLLBACK")
            
            # Estoque com filtros por produto (prioridade alta)
            if "estoque" in pergunta_lower or "quantidade" in pergunta_lower:
                if "produtos" in filters and filters["produtos"]:
                    produto = filters["produtos"][0]
                    estoque_produto = db.fetchone(
                        "SELECT SUM(es_totalestoque) as total FROM estoque WHERE LOWER(produto) LIKE %s",
                        [f"%{produto}%"]
                    )
                    if estoque_produto and estoque_produto[0]:
                        dados += f"O estoque de {produto} é de {float(estoque_produto[0]):,.2f} unidades.\n"
                        print(f"[Chat] Dados específicos encontrados para produto: {produto}")
                else:
                    # Fallback para estoque total
                    estoque_total = db.fetchone("SELECT SUM(es_totalestoque) as total FROM estoque")
                    if estoque_total and estoque_total[0]:
                        dados += f"O estoque total é de {float(estoque_total[0]):,.2f} unidades.\n"
            
            # Top produtos (sempre útil para contexto)
            produtos = db.fetchall(
                "SELECT produto, SUM(es_totalestoque) as total FROM estoque GROUP BY produto ORDER BY total DESC LIMIT 5"
            )
            if produtos:
                dados += "Top 5 produtos em estoque:\n"
                for row in produtos:
                    dados += f"- {row[0]}: {float(row[1]):,.2f} unidades\n"
            
            # SKU específico
            if "sku" in pergunta_lower or ("skus" in filters and filters["skus"]):
                sku = filters.get("skus", [None])[0] if "skus" in filters else None
                if not sku:
                    palavras = pergunta_lower.split()
                    for i, palavra in enumerate(palavras):
                        if "sku" in palavra and i + 1 < len(palavras):
                            sku = palavras[i + 1].upper()
                            break
                if sku:
                    estoque_sku = db.fetchall(
                        "SELECT produto, es_totalestoque, dias_em_estoque FROM estoque WHERE UPPER(SKU) LIKE %s",
                        [f"%{sku}%"]
                    )
                    if estoque_sku:
                        dados += f"Dados do SKU {sku}:\n"
                        for row in estoque_sku:
                            dados += f"- Produto: {row[0]}, Quantidade: {float(row[1]):,.2f}, Dias em estoque: {row[2]}\n"
                    else:
                        dados += f"SKU {sku} não encontrado.\n"
            
            if not dados:
                dados = "Não encontrei dados específicos para sua pergunta. Os dados disponíveis incluem informações de estoque e faturamento."
        
        except Exception as e:
            print(f"[Chat] Erro ao buscar dados específicos: {e}")
            dados = "Erro ao buscar dados. Tente novamente."
        
        return dados

    def _enriquecer_contexto(self, contexto: str, perguntas_similares: List[Dict]) -> str:
        if not perguntas_similares:
            return contexto
        contexto_knn = "\n\n=== PERGUNTAS SIMILARES DO HISTÓRICO (REFERÊNCIA APENAS) ===\n"
        for i, sim in enumerate(perguntas_similares, 1):
            contexto_knn += f"\n{i}. Pergunta: {sim['pergunta']}\n"
            contexto_knn += f"   Resposta: {sim['resposta']}\n"
            contexto_knn += f"   Similaridade: {sim.get('similaridade', 0):.1%}\n"
        return contexto + contexto_knn

    def _salvar_resposta(self, user_id: int, pergunta: str, resposta: str, db: NeonDB) -> int:
        try:
            db.execute("ROLLBACK")
            result = db.fetchone(
                """
                INSERT INTO mensagem (id_usuario, mensagem, ia, envio)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
                """,
                [user_id, resposta, True]
            )
            db.commit()
            print(f"[Chat] Resposta IA salva com ID: {result[0] if result else 'erro'}")
            return result[0] if result else None
        except Exception as e:
            print(f"[Chat] Erro ao salvar resposta: {e}")
            try:
                db.execute("ROLLBACK")
            except:
                pass
            return None

    def _obter_contexto_base(self, user_id: int, pergunta: str, analise: Dict[str, Any]) -> str:
        generate_context = getattr(self.context_service, "generate_context", None)
        if callable(generate_context):
            try:
                return generate_context(
                    analysis=analise,
                    user_id=user_id,
                    query_hint=pergunta
                )
            except TypeError:
                try:
                    return generate_context(analise)
                except TypeError:
                    pass
        return self.context_service.get_combined_context(user_id, query_hint=pergunta)

    def _criar_prompt_melhorado(
        self,
        pergunta: str,
        contexto: str,
        dados_especificos: str,
        analise: Dict[str, Any],
        tem_historico: bool = False
    ) -> str:
        focus = ", ".join(analise.get("focus", [])) or "estoque e faturamento"
        instrucoes_extra = ""
        if analise.get("requires_detailed_data"):
            instrucoes_extra = "\n8. Use dados detalhados (SKU/cliente) quando disponíveis."
        knn_aviso = (
            "\n9. IMPORTANTE: Se houver perguntas similares do histórico, use-as apenas como referência. Priorize sempre os dados concretos fornecidos acima."
            if tem_historico else ""
        )
        prompt = f"""Você é um assistente de análise de dados de negócio.

PERGUNTA DO USUÁRIO: {pergunta}
FOCO DA PERGUNTA (detecção automática): {focus}

DADOS DISPONÍVEIS PARA ANÁLISE:
{contexto}

{dados_especificos if dados_especificos else ""}

INSTRUÇÕES IMPORTANTES:
1. Analise TODOS os dados fornecidos acima
2. Responda de forma clara e natural, cite os dados exatos encontrados
3. Use números e fatos concretos dos dados
4. Se a pergunta for sobre estoque, foque nos dados de estoque (SKU, produto, quantidade, aging)
5. Se a pergunta for sobre faturamento, foque nos dados de faturamento (cliente, peso, giro)
6. Se não encontrar dados relevantes, informe claramente ao usuário
7. Seja objetivo e preciso{instrucoes_extra}{knn_aviso}

RESPOSTA:"""
        return prompt

    def testar_knn(self, user_id: int, pergunta: str, db: NeonDB) -> Dict[str, Any]:
        resultado_com_knn = self.processar_pergunta(user_id, pergunta, db, usar_knn=True)
        resultado_sem_knn = self.processar_pergunta(user_id, pergunta, db, usar_knn=False)
        return {
            "pergunta": pergunta,
            "com_knn": resultado_com_knn["mensagem"]["mensagem"],
            "sem_knn": resultado_sem_knn["mensagem"]["mensagem"]
        }