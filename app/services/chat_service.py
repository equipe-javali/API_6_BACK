from typing import Dict, Any, List
from db.neon_db import NeonDB
from models.conversation_model import ConversationModel
from services.agent_service import AgentService
from services.context_service import ContextService
from services.QueryAnalyzer import QueryAnalyzer  # novo
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
        """
        Processa uma pergunta do usuário usando o agente de IA e contexto do banco de dados
        
        Parameters:
        - user_id: ID do usuário
        - pergunta: Pergunta do usuário
        - db: Conexão com banco de dados
        - usar_knn: Flag para habilitar/desabilitar KNN (desabilitado por padrão até ter histórico suficiente)
        """
        print(f"[Chat] Processando pergunta: '{pergunta}'")
        
        try:
            # Resetar qualquer transação abortada
            db.execute("ROLLBACK")
            
            # 0. Análise da pergunta 
            analise = self.query_analyzer.analyze_query(pergunta)
            print(f"[Chat] Análise obtida: {analise}")
            
            # 1. Buscar histórico do usuário para KNN (se habilitado) - desabilitado por padrão temporariamente
            historico_usuario = []  # Temporariamente desabilitado até termos histórico suficiente
            perguntas_similares = [] # Temporariamente desabilitado até termos histórico suficiente
            
            if usar_knn:
                historico_usuario = self._buscar_historico_usuario(user_id, db, limite=20)
                perguntas_similares = self._knn_buscar_similares(pergunta, historico_usuario, k=3)
            
            # 3. Obter contexto relevante
            contexto = self._obter_contexto_base(user_id, pergunta, analise)
            print(f"[Chat] Contexto base: {len(contexto)} caracteres")
            
            # 4. Buscar dados específicos (estoque ou faturamento)
            dados_especificos = self._buscar_dados_especificos(pergunta, db)
            
            # 5. Enriquecer contexto com perguntas similares (se houver) - só usa se KNN estiver habilitado
            contexto_enriquecido = contexto
            if usar_knn and perguntas_similares:
                contexto_enriquecido = self._enriquecer_contexto(contexto, perguntas_similares)
            
            # 6. Criar prompt direcionado
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
            
            # 7. Processar a pergunta usando o agente
            print(f"[Chat] Chamando AgentService.process_input com pergunta='{pergunta}'")
            resposta = self.agent.process_input(pergunta, prompt_final)
            
            print(f"[Chat] Resposta gerada: '{resposta}'")
            
            # 8. Salvar no banco
            saved_id = self._salvar_resposta(user_id, pergunta, resposta, db)
            
            conversation = ConversationModel(
                user_id=user_id,
                pergunta=pergunta,
                resposta=resposta
            )
            conversation.id = saved_id
            
            return {
                "success": True,
                "conversation": conversation.to_dict()
            }
            
        except Exception as e:
            print(f"[Chat] Erro no processamento: {e}")
            # Garantir rollback em caso de erro
            try:
                db.execute("ROLLBACK")
            except:
                pass
            
            # Resposta de fallback
            resposta = f"Desculpe, não consegui processar sua pergunta no momento."
            return {
                "success": False,
                "conversation": {
                    "user_id": user_id,
                    "pergunta": pergunta,
                    "resposta": resposta
                }
            }
    
    def _buscar_historico_usuario(self, user_id: int, db: NeonDB, limite: int = 20) -> List[Dict]:
        """Busca o histórico de perguntas do usuário para usar no KNN"""
        try:
            # Resetar transações anteriores
            db.execute("ROLLBACK")
            
            # Verifica se a tabela existe
            tabela_existe = db.fetchone(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversation'
                )
                """
            )
            
            # Se a tabela não existe, cria-a
            if not tabela_existe or not tabela_existe[0]:
                print("[KNN] Criando tabela conversation...")
                db.execute("""
                CREATE TABLE IF NOT EXISTS conversation (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    pergunta TEXT NOT NULL,
                    resposta TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
                """)
                db.commit()
                return []
            
            resultados = db.fetchall(
                """
                SELECT pergunta, resposta, timestamp
                FROM conversation
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                [user_id, limite]
            )
            
            if resultados:
                historico = [{"pergunta": row[0], "resposta": row[1], "timestamp": str(row[2])} for row in resultados]
                print(f"[KNN] Histórico do usuário {user_id}: {len(historico)} registros encontrados")
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
        """
        Usa KNN (TF-IDF + Cosine Similarity) para encontrar perguntas similares
        Filtra respostas com erros ou baixa similaridade
        """
        if not historico or len(historico) < 2:
            return []
        
        try:
            # Preparar documentos
            perguntas_historico = [h["pergunta"] for h in historico]
            todos_documentos = [pergunta] + perguntas_historico
            
            # Adicionar logs detalhados
            print(f"[KNN DEBUG] Pergunta atual: '{pergunta}'")
            
            # TF-IDF Vectorizer - sem stop_words para evitar erro
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(todos_documentos)
            
            # Calcular similaridade com cosine
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
            
            # Obter top K
            top_indices = np.argsort(similarities)[::-1][:k]
            
            # Filtrar respostas ruins - MELHORADO
            frases_erro = [
                "desculpe", "erro", "não consegui", "ocorreu um erro", 
                "falha", "tente novamente", "tente ser mais específico"
            ]
            
            similares = []
            for idx in top_indices:
                sim_score = float(similarities[idx])
                if sim_score > 0.3:  # Threshold aumentado de 0.1 para 0.3
                    resposta_lower = historico[idx]["resposta"].lower()
                    # Só adiciona se não contiver frases de erro
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
        """Busca dados específicos quando menciona SKU, estoque ou faturamento"""
        dados = ""
        pergunta_lower = pergunta.lower()
        
        try:
            # Resetar qualquer transação abortada antes de começar
            db.execute("ROLLBACK")
            
            # 1. Se pergunta sobre faturamento
            if "faturamento" in pergunta_lower or "vendas" in pergunta_lower:
                dados += self._buscar_dados_faturamento(pergunta_lower, db)
            
            # 2. Se pergunta sobre estoque em geral ou quantidade
            if "estoque" in pergunta_lower or "quantidade" in pergunta_lower:
                dados += self._buscar_dados_estoque(pergunta_lower, db)
            
        except Exception as e:
            print(f"[Chat] Erro ao buscar dados específicos: {e}")
            try:
                db.execute("ROLLBACK")
            except:
                pass
        
        return dados
    
    def _buscar_dados_faturamento(self, pergunta_lower: str, db: NeonDB) -> str:
        """Busca dados específicos sobre faturamento"""
        dados = ""
        try:
            db.execute("ROLLBACK")
            
            # Resumo de faturamento
            faturamento = db.fetchone(
                "SELECT COUNT(*) as total, SUM(zs_peso_liquido) as total_peso FROM faturamento"
            )
            
            if faturamento:
                dados += "\n=== RESUMO DE FATURAMENTO ===\n"
                dados += f"Total de registros: {faturamento[0]}\n"
                dados += f"Peso total: {faturamento[1]}\n\n"
            
            # Top produtos por peso
            produtos = db.fetchall(
                """
                SELECT produto, SUM(zs_peso_liquido) as peso_total 
                FROM faturamento 
                GROUP BY produto 
                ORDER BY peso_total DESC 
                LIMIT 5
                """
            )
            
            if produtos:
                dados += "=== TOP 5 PRODUTOS POR PESO ===\n"
                for row in produtos:
                    dados += f"- {row[0]}: {row[1]} unidades\n"
            
            print(f"[Chat] Dados de faturamento: {len(dados)} caracteres")
            
        except Exception as e:
            print(f"[Chat] Erro ao buscar dados de faturamento: {e}")
            db.execute("ROLLBACK")
        
        return dados
    
    def _buscar_dados_estoque(self, pergunta_lower: str, db: NeonDB) -> str:
        """Busca dados específicos sobre estoque"""
        dados = ""
        try:
            # Rollback explícito antes de cada consulta
            db.execute("ROLLBACK")
            
            # Se menciona SKU específico
            if "sku" in pergunta_lower and len(pergunta_lower.split()) > 1:
                palavras = pergunta_lower.split()
                for i, palavra in enumerate(palavras):
                    if "sku" in palavra and i + 1 < len(palavras):
                        possivel_sku = palavras[i + 1].upper()
                        
                        # Buscar SKU específico
                        estoque = db.fetchall(
                            "SELECT sku, produto, es_totalestoque as quantidade, dias_em_estoque as aging FROM estoque WHERE UPPER(sku) LIKE %s",
                            [f"%{possivel_sku}%"]
                        )
                        
                        if estoque:
                            dados += f"\n=== DADOS DO SKU {possivel_sku} ===\n"
                            for row in estoque:
                                dados += f"SKU: {row[0]}\nProduto: {row[1]}\nQuantidade: {row[2]}\nAging: {row[3]} dias\n\n"
                        else:
                            dados += f"\n=== SKU {possivel_sku} NÃO ENCONTRADO ===\n"
                        break
            
            # Se pergunta sobre reposição / estoque baixo
            if any(palavra in pergunta_lower for palavra in ["reposição", "repor", "estoque baixo", "precisam", "precisa"]):
                # Threshold configurável — ajuste conforme necessidade
                threshold = 10
                try:
                    itens_baixo_estoque = db.fetchall(
                        """
                        SELECT sku, produto, es_totalestoque as quantidade
                        FROM estoque
                        WHERE es_totalestoque <= %s
                        ORDER BY es_totalestoque ASC
                        LIMIT 50
                        """,
                        [threshold]
                    )

                    if itens_baixo_estoque:
                        dados += f"\n=== ITENS COM ESTOQUE BAIXO (<= {threshold}) ===\n"
                        for row in itens_baixo_estoque:
                            dados += f"- SKU: {row[0]} | Produto: {row[1]} | Quantidade: {row[2]}\n"
                    else:
                        dados += "\n=== NENHUM ITEM COM ESTOQUE CRÍTICO ===\n"

                    print(f"[Chat] Itens com estoque baixo encontrados: {len(itens_baixo_estoque) if itens_baixo_estoque else 0}")
                    return dados
                except Exception as e:
                    print(f"[Chat] Erro ao consultar itens com estoque baixo: {e}")
                    try:
                        db.execute("ROLLBACK")
                    except:
                        pass

            # Se pergunta genérica sobre estoque/quantidade (sem SKU específico)
            else:
                # Consulta de total em estoque (mais robusta)
                estoque_total = db.fetchone(
                    "SELECT SUM(es_totalestoque) as total FROM estoque"
                )
                
                if estoque_total and estoque_total[0]:
                    dados += f"\n=== QUANTIDADE TOTAL EM ESTOQUE ===\n"
                    dados += f"Total de itens em estoque: {estoque_total[0]}\n\n"
                
                # Top produtos por quantidade
                db.execute("ROLLBACK") # Garante transação limpa
                produtos = db.fetchall(
                    """
                    SELECT produto, SUM(es_totalestoque) as total 
                    FROM estoque 
                    GROUP BY produto 
                    ORDER BY total DESC
                    LIMIT 5
                    """
                )
                
                if produtos:
                    dados += "=== QUANTIDADE POR PRODUTO ===\n"
                    for row in produtos:
                        dados += f"- {row[0]}: {row[1]} unidades\n"
            
            print(f"[Chat] Dados específicos de estoque: {len(dados)} caracteres")
            
        except Exception as e:
            print(f"[Chat] Erro ao buscar dados específicos de estoque: {e}")
            db.execute("ROLLBACK")
        
        return dados
    
    def _enriquecer_contexto(self, contexto: str, perguntas_similares: List[Dict]) -> str:
        """Adiciona perguntas similares ao contexto com aviso sobre possíveis erros"""
        if not perguntas_similares:
            return contexto
        
        # Adicionado aviso sobre possibilidade de erros
        contexto_knn = "\n\n=== PERGUNTAS SIMILARES DO HISTÓRICO (REFERÊNCIA APENAS) ===\n"
        for i, sim in enumerate(perguntas_similares, 1):
            contexto_knn += f"\n{i}. Pergunta: {sim['pergunta']}\n"
            contexto_knn += f"   Resposta: {sim['resposta']}\n"
            contexto_knn += f"   Similaridade: {sim.get('similaridade', 0):.1%}\n"
        
        return contexto + contexto_knn
    
    def _salvar_resposta(self, user_id: int, pergunta: str, resposta: str, db: NeonDB) -> int:
        """Salva a pergunta e resposta no banco de dados"""
        try:
            # Resetar transações anteriores
            db.execute("ROLLBACK")
            
            result = db.fetchone(
                """
                INSERT INTO conversation (user_id, pergunta, resposta, timestamp)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
                """,
                [user_id, pergunta, resposta]
            )
            
            db.commit()
            print(f"[Chat] Resposta salva com ID: {result[0] if result else 'erro'}")
            return result[0] if result else None
            
        except Exception as e:
            print(f"[Chat] Erro ao salvar resposta: {e}")
            try:
                db.execute("ROLLBACK")
            except:
                pass
            return None
    
    def _obter_contexto_base(self, user_id: int, pergunta: str, analise: Dict[str, Any]) -> str:
        """
        Usa a mesma lógica do test_full_flow:
        - se ContextService tiver generate_context, usa-o
        - caso contrário, cai no get_combined_context
        """
        generate_context = getattr(self.context_service, "generate_context", None)
        if callable(generate_context):
            try:
                return generate_context(
                    analysis=analise,
                    user_id=user_id,
                    query_hint=pergunta
                )
            except TypeError:
                # fallback para assinaturas antigas
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
        """Cria um prompt claro e alinhado com a análise obtida"""
        focus = ", ".join(analise.get("focus", [])) or "estoque e faturamento"
        instrucoes_extra = ""
        if analise.get("requires_detailed_data"):
            instrucoes_extra = "\n8. Use dados detalhados (SKU/cliente) quando disponíveis."
        
        # Incluir aviso para ignorar respostas históricas com erro (quando houver histórico)
        knn_aviso = "\n9. IMPORTANTE: Se houver perguntas similares do histórico, use-as apenas como referência. Priorize sempre os dados concretos fornecidos acima." if tem_historico else ""
        
        prompt = f"""Você é um assistente de análise de dados de negócio.

PERGUNTA DO USUÁRIO: {pergunta}
FOCO DA PERGUNTA (detecção automática): {focus}

DADOS DISPONÍVEIS PARA ANÁLISE:
{contexto}

{dados_especificos if dados_especificos else ""}

INSTRUÇÕES IMPORTANTES:
1. Analise TODOS os dados fornecidos acima
2. Responda de forma específica baseada nos dados reais
3. Use números e fatos concretos dos dados
4. Se a pergunta for sobre estoque, foque nos dados de estoque (SKU, produto, quantidade, aging)
5. Se a pergunta for sobre faturamento, foque nos dados de faturamento (cliente, peso, giro)
6. Se não encontrar dados relevantes, informe claramente
7. Seja objetivo e preciso{instrucoes_extra}{knn_aviso}

RESPOSTA:"""
        
        return prompt

    def testar_knn(self, user_id: int, pergunta: str, db: NeonDB) -> Dict[str, Any]:
        """
        Método para testar o impacto do KNN nas respostas
        Retorna respostas com e sem KNN para comparação
        """
        # Com KNN
        resultado_com_knn = self.processar_pergunta(user_id, pergunta, db, usar_knn=True)
        
        # Sem KNN
        resultado_sem_knn = self.processar_pergunta(user_id, pergunta, db, usar_knn=False)
        
        return {
            "pergunta": pergunta,
            "com_knn": resultado_com_knn["conversation"]["resposta"],
            "sem_knn": resultado_sem_knn["conversation"]["resposta"]
        }