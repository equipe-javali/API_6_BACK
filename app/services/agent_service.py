import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from db.neon_db import execute_query
import re
from decimal import Decimal
from services.QueryAnalyzer import QueryAnalyzer  # Importar QueryAnalyzer para PLN

load_dotenv()

class AgentService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("AgentService using device:", self.device)
        
        # Usar mesmo modelo do BoletimService para consistência
        HG_TOKEN = os.getenv("HG_TOKEN")
        if self.device.type == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-3-1b-pt",  
                token=HG_TOKEN,
                device_map="auto",
                dtype=torch.bfloat16,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-3-1b-pt",  
                low_cpu_mem_usage=True,
            )
            self.model.to(self.device, dtype=torch.float32)

        self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-1b-pt") 
        
        # Cache para otimização
        self._cache = {}
        self._cache_max_size = 100
        
        # Instanciar QueryAnalyzer para PLN
        self.query_analyzer = QueryAnalyzer()
    
    def processar_pergunta_simples(self, pergunta: str) -> str:
        """Processa pergunta sem contexto adicional - só IA pura"""
        if not pergunta or not pergunta.strip():
            return "Por favor, faça uma pergunta válida."
        
        # Verificar cache
        cache_key = f"simple_{hash(pergunta)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"""Você é um assistente de análise de dados empresariais. O usuário fez um questionamento:
        
        PERGUNTA DO USUÁRIO: {pergunta}

        Responda de forma clara, objetiva e profissional em português.
        Se não for uma pergunta retorne: Faça uma pergunta válida.
        Se a pergunta não for sobre análise de dados empresariais responda: Não domino esse assunto, faça outra pergunta.
        """
        
        try:
            response = self._generate_response(prompt)
            
            # Salvar no cache
            if len(self._cache) >= self._cache_max_size:
                # Remove o mais antigo (FIFO simples)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[cache_key] = response
            return response
            
        except Exception as e:
            return f"Erro ao processar pergunta: {str(e)}"
    
    def processar_pergunta_com_contexto(self, pergunta: str, contexto: str) -> str:
        """Processa pergunta com contexto fornecido pelo ContextService"""
        if not pergunta or not pergunta.strip():
            return "Por favor, faça uma pergunta válida."
        
        prompt = f"""Você é um assistente de análise de dados empresariais especializado em estoque e faturamento.
        
        {contexto}
        
        PERGUNTA DO USUÁRIO: {pergunta}
        
        Responda de forma clara e objetiva, baseando-se apenas nos dados fornecidos no contexto.
        Se a pergunta não puder ser respondida com os dados disponíveis, informe isso claramente.
        """
        
        try:
            return self._generate_response(prompt)
        except Exception as e:
            return f"Erro ao processar pergunta: {str(e)}"
    
   
    def _generate_response(self, prompt: str) -> str:
        """Gera resposta com limpeza aprimorada para remover lixo"""
        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            input_ids = {k: v.to(self.device) for k, v in input_ids.items()}
    
            with torch.no_grad():
                outputs = self.model.generate(
                    **input_ids, 
                    max_new_tokens=30,
                    temperature=0.1,
                    do_sample=False,
                    repetition_penalty=2.0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            output_str = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Limpeza aprimorada: remover prompt, HTML, repetições e lixo
            response = output_str.replace(prompt, "").strip()
            response = re.sub(r'Responda de forma.*?:\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'Resposta:\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'- ".*?"', '', response).strip()
            response = re.sub(r'<[^>]+>', '', response).strip()  # Remover HTML
            response = re.sub(r'\*+', '', response).strip()  # Remover asteriscos
            
            # Detectar e remover repetições
            words = response.split()
            if len(words) > 4:
                half_len = len(words) // 2
                if words[:half_len] == words[half_len:half_len*2]:
                    response = ' '.join(words[:half_len])
            
            response = re.sub(r'(\b\w+\b)(\s+\1)+', r'\1', response)
            
            # Limitar tamanho
            if len(response) > 150:
                response = response[:147] + "..."
            
            print(f"[DEBUG IA] Resposta limpa: '{response}' (len: {len(response)})")
            return response if response else "Não foi possível gerar uma resposta adequada."
        
        except Exception as e:
            print(f"[ERRO IA] Falha na geração: {e}")
            return "Erro na geração de resposta IA."
    
    def clear_cache(self):
        """Limpa o cache de respostas"""
        self._cache.clear()
    
   
    def generate_sql(self, pergunta: str, contexto: str, analise: dict = None) -> str:
        """Gera SQL com filtros temporais garantidos"""
        if analise is None:
            analise = self.query_analyzer.analyze_query(pergunta)
        
        filters = analise.get("filters", {})
        focus = analise.get("focus", [])
        
        print(f"[DEBUG AgentService] Filtros PLN recebidos: {filters}")
        
        # Determinar tabela
        if "faturamento" in focus or "vendas" in pergunta.lower() or "faturamento" in pergunta.lower():
            tabela = "faturamento"
            coluna_soma = "zs_peso_liquido"  # Nota: Se for valor monetário, ajustar coluna
            coluna_data = "data"
        else:
            tabela = "estoque"
            coluna_soma = "es_totalestoque"
            coluna_data = "data"
        
        base_query = f"SELECT SUM({coluna_soma}) as total FROM {tabela}"
        
        conditions = []
        
        # Filtros temporais (prioridade alta)
        if "data_inicio" in filters and "data_fim" in filters:
            conditions.append(f"{coluna_data} >= '{filters['data_inicio']}' AND {coluna_data} < '{filters['data_fim']}'")
            print(f"[DEBUG AgentService] Aplicando filtro temporal: {filters['data_inicio']} a {filters['data_fim']}")
        
        # Filtros de produtos
        if "produtos" in filters and filters["produtos"]:
            produto_conditions = []
            for produto in filters["produtos"]:
                produto_conditions.append(f"LOWER(produto) LIKE '%{produto}%'")
            if produto_conditions:
                conditions.append(f"({' OR '.join(produto_conditions)})")
        
        # Filtros de SKUs
        if "skus" in filters and filters["skus"]:
            sku_conditions = []
            for sku in filters["skus"]:
                sku_conditions.append(f"UPPER(SKU) LIKE '%{sku.upper()}%'")
            if sku_conditions:
                conditions.append(f"({' OR '.join(sku_conditions)})")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            print(f"[DEBUG AgentService] Query final: {base_query}")
        else:
            print("[DEBUG AgentService] Nenhum filtro aplicado")
        
        return base_query
    
    # ...existing code...
    
    def _generate_sql_with_ai(self, pergunta: str, contexto: str) -> str:
        """Fallback: Gera SQL usando IA (método original)"""
        schema_info = """
ESQUEMA DAS TABELAS:

ESTOQUE:
- data (date): Data do registro
- cod_cliente (int): Código do cliente  
- es_centro (text): Centro
- tipo_material (text): Tipo do material
- origem (text): Origem
- cod_produto (text): Código do produto
- lote (text): Lote
- dias_em_estoque (int): Dias em estoque
- produto (text): Nome do produto (ex: Bobina, Rolo, Chapa, Tira)
- grupo_mercadoria (text): Grupo da mercadoria (ex: Laminado a Frio, Zincado)
- es_totalestoque (decimal): Valor numérico em es_totalestoque
- SKU (text): SKU do produto

FATURAMENTO:
- data (date): Data do faturamento
- cod_cliente (int): Código do cliente
- lote (text): Lote
- origem (text): Origem
- zs_gr_mercad (text): Grupo mercadoria
- produto (text): Nome do produto
- cod_produto (text): Código do produto
- zs_centro (text): Centro
- zs_cidade (text): Cidade
- zs_uf (text): UF/Estado
- zs_peso_liquido (decimal): Peso líquido numérico
- giro_sku_cliente (decimal): Valor de giro numérico
- SKU (text): SKU do produto
"""
        
        prompt = f"""<start_of_turn>user
Você é um especialista em SQL PostgreSQL. Gere APENAS a query SQL para responder à pergunta factual sobre os dados.

{schema_info}

PERGUNTA: {pergunta}

REGRAS IMPORTANTES:
- Use APENAS as tabelas "estoque" e "faturamento" (em minúsculas)
- Para "maior es_totalestoque" use ORDER BY es_totalestoque DESC LIMIT 1
- Para "todos os produtos" use SELECT DISTINCT produto FROM estoque
- Para "quantos registros" use COUNT(*)
- Para "soma" use SUM()
- Nomes de colunas exatos: es_totalestoque, zs_peso_liquido, etc.
- Sempre use LIMIT quando apropriado

Gere APENAS a query SQL:
<end_of_turn>
<start_of_turn>model
SELECT"""
        
        input_ids = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **input_ids,
                max_new_tokens=100,
                temperature=0.1,  # Mais determinístico
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decodificar apenas os novos tokens gerados
        new_tokens = outputs[0][input_ids['input_ids'].shape[1]:]
        sql_response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        # Limpar a resposta
        sql_query = sql_response.strip()
        sql_query = re.sub(r'```sql|```', '', sql_query).strip()
        
        # Garantir que começa com SELECT
        if not sql_query.upper().startswith('SELECT'):
            sql_query = f"SELECT {sql_query}"
        
        # Fallbacks específicos
        pergunta_lower = pergunta.lower()
        if 'maior' in pergunta_lower and 'es_totalestoque' in pergunta_lower:
            sql_query = "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque DESC LIMIT 1"
        elif 'todos os produtos' in pergunta_lower or 'listar produtos' in pergunta_lower:
            sql_query = "SELECT DISTINCT produto FROM estoque ORDER BY produto"
        elif 'quantos produtos' in pergunta_lower:
            if 'faturamento' in pergunta_lower:
                sql_query = "SELECT COUNT(DISTINCT produto) as total_produtos FROM faturamento"
            else:
                sql_query = "SELECT COUNT(DISTINCT produto) as total_produtos FROM estoque"
        elif 'quantos registros' in pergunta_lower:
            if 'faturamento' in pergunta_lower:
                sql_query = "SELECT COUNT(*) as total_registros FROM faturamento"
            else:
                sql_query = "SELECT COUNT(*) as total_registros FROM estoque"
        
        return sql_query.strip()
    
    def format_sql_response(self, pergunta: str, sql_result: list, contexto: str = "", analise: dict = None) -> str:
        """Formata resultado SQL usando PLN e contexto"""
        if not sql_result:
            return "Nenhum resultado encontrado para esta consulta."
        
        pergunta_lower = pergunta.lower()
        pergunta_normalizada = self.query_analyzer._normalize_text(pergunta_lower)
        
        if analise is None:
            analise = self.query_analyzer.analyze_query(pergunta)
        filters = analise.get("filters", {})

        # Tenta usar o produto identificado pelo PLN
        produto = None
        if "produtos" in filters and filters["produtos"]:
            produto = filters["produtos"][0]
        else:
            # Se não encontrou pelo PLN, tenta pegar do resultado SQL
            if sql_result and "produto" in sql_result[0]:
                produto = sql_result[0]["produto"]

        # Para perguntas sobre quantidade/estoque
        if ('quantidade' in pergunta_normalizada or 'estoque' in pergunta_normalizada or 'total' in pergunta_normalizada):
            if produto:
                total = sql_result[0].get('total', 0)
                if isinstance(total, Decimal):
                    total = float(total)
                return f"A quantidade de {produto} em estoque é de {total:,.2f} unidades."
        
        # Para perguntas sobre faturamento
        if 'faturamento' in pergunta_normalizada or 'vendas' in pergunta_normalizada:
            if sql_result and len(sql_result) > 0:
                total = sql_result[0].get('total', 0)
                if isinstance(total, Decimal):
                    total = float(total)
                periodo = ""
                if 'mes' in filters and 'ano' in filters:
                    mes_nome = list(self.query_analyzer.meses.keys())[filters['mes'] - 1]
                    periodo = f"no mês de {mes_nome} de {filters['ano']}"
                return f"O faturamento {periodo} foi de R$ {total:,.2f}."         
        
        # Respostas factuais específicas (mantidas do original)
        if 'maior' in pergunta_normalizada and 'es_totalestoque' in pergunta_normalizada:
            if sql_result and len(sql_result) > 0:
                item = sql_result[0]
                produto = item.get('produto', 'N/A')
                valor = item.get('es_totalestoque', 0)
                return f"Produto: {produto}, es_totalestoque: {valor}"
        
        elif 'todos os produtos' in pergunta_normalizada or 'listar produtos' in pergunta_normalizada:
            produtos = [item.get('produto', 'N/A') for item in sql_result]
            return f"Produtos encontrados: {', '.join(produtos[:10])}" + ("..." if len(produtos) > 10 else "")
        
        elif 'quantos' in pergunta_normalizada:
            if sql_result and len(sql_result) > 0:
                total = sql_result[0].get('total_produtos') or sql_result[0].get('total_registros') or sql_result[0].get('count', 0)
                return f"Total: {total}"
        
        # Formato genérico factual
        if len(sql_result) == 1:
            item = sql_result[0]
            campos = [f"{k}: {v}" for k, v in item.items()]
            return f"Resultado: {', '.join(campos)}"
        else:
            total = len(sql_result)
            primeiro = sql_result[0]
            campos = [f"{k}: {v}" for k, v in primeiro.items()]
            return f"Encontrados {total} registros. Primeiro: {', '.join(campos)}"
    
    def process_input(self, pergunta: str, contexto: str, analise: dict = None) -> str:
        """Método principal que integra SQL + IA + PLN para respostas conversacionais"""
        try:
            # 1. Gerar SQL usando PLN
            sql_query = self.generate_sql(pergunta, contexto, analise=analise)
            print(f"\nSQL gerada: {sql_query}")
            
            # 2. Executar SQL
            sql_result = execute_query(sql_query)
            print(f"Resultado SQL: {sql_result}")
            
            # 3. Formatar resposta conversacional usando IA
            final_response = self._generate_conversational_response(pergunta, sql_result, contexto, analise)
            
            return final_response
            
        except Exception as e:
            print(f"Erro: {str(e)}")
            return f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}"
 
    
    def _generate_conversational_response(self, pergunta: str, sql_result: list, contexto: str, analise: dict = None) -> str:
        """Gera resposta conversacional otimizada"""
        if not sql_result:
            return "Não encontrei dados relevantes para sua pergunta nos registros disponíveis."
        
        if analise is None:
            analise = self.query_analyzer.analyze_query(pergunta)
    
        filters = analise.get("filters", {})
    
        # Preparar dados concisos
        dados_extraidos = self._format_sql_for_ai(sql_result, filters)
    
        # Prompt mais direto e conversacional
        prompt = f"""Você é um assistente de dados empresariais amigável.
    
    Pergunta: {pergunta}
    
    Dados encontrados: {dados_extraidos}
    
    Responda de forma natural e direta em português, mencionando os números exatos de forma clara."""
    
        try:
            response = self._generate_response(prompt)
            if response and len(response) <= 100 and not any(word in response.lower() for word in ['responda', 'resposta']):
                return response.strip()
            else:
                # Fallback para formatação estruturada
                return self._format_fallback_response(pergunta, sql_result, filters)
        except Exception as e:
            print(f"[ERRO Conversacional] {e}")
            return self._format_fallback_response(pergunta, sql_result, filters)
    
    def _format_fallback_response(self, pergunta: str, sql_result: list, filters: dict) -> str:
        """Fallback conversacional com unidades corretas"""
        pergunta_lower = pergunta.lower()
        
        if 'produtos' in filters and filters['produtos']:
            produto = filters['produtos'][0]
            if sql_result and len(sql_result) > 0:
                total = sql_result[0].get('total', 0)
                if isinstance(total, Decimal):
                    total = float(total)
                return f"Atualmente temos {total:,.2f} unidades de {produto} em estoque."
        
        if 'faturamento' in pergunta_lower or 'vendas' in pergunta_lower:
            if sql_result and len(sql_result) > 0:
                total = sql_result[0].get('total', 0)
                if isinstance(total, Decimal):
                    total = float(total)
                periodo = ""
                if 'periodo' in filters:
                    periodo = f" no período de {filters['periodo']}"
                elif 'mes' in filters and 'ano' in filters:
                    mes_nome = list(self.query_analyzer.meses.keys())[filters['mes'] - 1]
                    periodo = f" em {mes_nome} de {filters['ano']}"
                return f"O faturamento{periodo} foi de R$ {total:,.2f}."  # Corrigido para R$
        
        # Genérico
        if sql_result and len(sql_result) > 0 and 'total' in sql_result[0]:
            total = sql_result[0]['total']
            if isinstance(total, Decimal):
                total = float(total)
            # Determinar unidade baseada na tabela
            unidade = "R$" if 'faturamento' in pergunta_lower else "unidades"
            return f"O valor encontrado foi de {unidade} {total:,.2f}."


    def _format_sql_for_ai(self, sql_result: list, filters: dict) -> str:
        """Formata resultado SQL para input da IA"""
        if not sql_result:
            return "Nenhum dado encontrado."
        
        formatted = ""
        
        # Informações sobre filtros aplicados
        if filters:
            filter_info = []
            if 'produtos' in filters:
                filter_info.append(f"Produtos filtrados: {', '.join(filters['produtos'])}")
            if 'data_inicio' in filters and 'data_fim' in filters:
                filter_info.append(f"Período: {filters['data_inicio']} a {filters['data_fim']}")
            if 'skus' in filters:
                filter_info.append(f"SKUs: {', '.join(filters['skus'])}")
            
            if filter_info:
                formatted += f"Filtros aplicados: {'; '.join(filter_info)}\n\n"
        
        # Dados numéricos
        if len(sql_result) == 1 and 'total' in sql_result[0]:
            total = sql_result[0]['total']
            if isinstance(total, Decimal):
                total = float(total)
            formatted += f"Valor total encontrado: {total:,.2f}"
        else:
            formatted += f"Registros encontrados: {len(sql_result)}\n"
            for i, row in enumerate(sql_result[:5]):  # Limitar a 5 registros
                formatted += f"Registro {i+1}: {', '.join([f'{k}: {v}' for k, v in row.items()])}\n"
        
        return formatted

if __name__ == "__main__":
    agent = AgentService()
    pergunta = input("Digite sua pergunta: ")
    print(agent.processar_pergunta_simples(pergunta))