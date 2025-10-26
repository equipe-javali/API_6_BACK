import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from db.neon_db import execute_query
import re
from decimal import Decimal
from services.QueryAnalyzer import QueryAnalyzer

load_dotenv()

class AgentService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("AgentService using device:", self.device)
        
        HG_TOKEN = os.getenv("HG_TOKEN")
        model_name = os.getenv("HF_MODEL", "google/gemma-3-1b-pt")
        if self.device.type == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                token=HG_TOKEN,
                device_map="auto",
                dtype=torch.bfloat16,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                low_cpu_mem_usage=True,
            )
            self.model.to(self.device, dtype=torch.float32)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._cache = {}
        self._cache_max_size = 100
        self.query_analyzer = QueryAnalyzer()
    
    def processar_pergunta_simples(self, pergunta: str) -> str:
        if not pergunta or not pergunta.strip():
            return "Por favor, faça uma pergunta válida."
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
            if len(self._cache) >= self._cache_max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = response
            return response
        except Exception as e:
            return f"Erro ao processar pergunta: {str(e)}"
    
    def processar_pergunta_com_contexto(self, pergunta: str, contexto: str) -> str:
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
        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            input_ids = {k: v.to(self.device) for k, v in input_ids.items()}
            with torch.no_grad():
                outputs = self.model.generate(
                    **input_ids,
                    max_new_tokens=100,
                    temperature=0.1,
                    do_sample=False,
                    repetition_penalty=2.0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            output_str = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = output_str.replace(prompt, "").strip()
            response = re.sub(r'Responda de forma.*?:\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'Resposta:\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'- ".*?"', '', response).strip()
            response = re.sub(r'<[^>]+>', '', response).strip()
            response = re.sub(r'\*+', '', response).strip()
            words = response.split()
            if len(words) > 4:
                half_len = len(words) // 2
                if words[:half_len] == words[half_len:half_len*2]:
                    response = ' '.join(words[:half_len])
            response = re.sub(r'(\b\w+\b)(\s+\1)+', r'\1', response)
            if len(response) > 150:
                response = response[:147] + "..."
            print(f"[DEBUG IA] Resposta limpa: '{response}' (len: {len(response)})")
            return response if response else "Não foi possível gerar uma resposta adequada."
        except Exception as e:
            print(f"[ERRO IA] Falha na geração: {e}")
            return "Erro na geração de resposta IA."
    
    def clear_cache(self):
        self._cache.clear()
    
    def generate_sql(self, pergunta: str, contexto: str, analise: dict = None) -> str:
        """Gera SQL usando análise PLN + templates inteligentes"""
        if analise is None:
            analise = self.query_analyzer.analyze_query(pergunta)

        if not analise:
            return "SELECT COUNT(*) as total FROM estoque"

        filters = analise.get("filters", {})
        focus = analise.get("focus", [])
        pergunta_lower = pergunta.lower()

        # Estratégia: usar templates SQL baseados em padrões de pergunta + filtros PLN
        sql_query = self._generate_sql_from_template(pergunta_lower, filters, focus)

        print(f"[SQL Template] Query gerada: {sql_query}")
        return sql_query

    def _generate_sql_from_template(self, pergunta: str, filters: dict, focus: list) -> str:
        """Gera SQL usando templates inteligentes baseados em padrões"""

        # Determinar tabela prioritária baseada na pergunta explícita
        pergunta_lower = pergunta.lower()
        
        # Prioridade: se a palavra aparece explicitamente na pergunta, usar ela
        if 'faturamento' in pergunta_lower or 'vendas' in pergunta_lower or 'venda' in pergunta_lower:
            table = 'faturamento'
        elif 'estoque' in pergunta_lower or 'estoques' in pergunta_lower:
            table = 'estoque'
        # Se não há menção explícita, usar o foco determinado pelo QueryAnalyzer
        elif 'faturamento' in focus:
            table = 'faturamento'
        elif 'estoque' in focus:
            table = 'estoque'
        else:
            table = 'estoque'  # default

        # Template 1: Contagem de registros
        if any(word in pergunta for word in ['quantos', 'quantas', 'número de', 'total de', 'contar']):
            base_query = f"SELECT COUNT(*) as total FROM {table}"

            # Adicionar filtros
            conditions = self._build_conditions(filters, table)
            if conditions:
                base_query += f" WHERE {' AND '.join(conditions)}"

            return base_query

        # Template 3: Listar produtos únicos
        elif any(word in pergunta for word in ['quais produtos', 'listar produtos', 'produtos disponíveis', 'tipos de produto', 'todos os produtos', 'nome de todos os produtos', 'informe o nome', 'informe']):
            return f"SELECT DISTINCT produto FROM {table} ORDER BY produto"

        # Template 2: Soma de valores - ajustar para não capturar perguntas sobre data
        elif any(word in pergunta for word in ['quanto', 'qual o total', 'soma', 'valor total', 'faturamento', 'qual o faturamento', 'faturamento total']) and not any(word in pergunta for word in ['data', 'registros mais antig', 'mais antig']):
            if table == 'estoque':
                column = 'es_totalestoque'
            else:
                column = 'zs_peso_liquido'

            base_query = f"SELECT SUM({column}) as total FROM {table}"

            # Adicionar filtros
            conditions = self._build_conditions(filters, table)
            if conditions:
                base_query += f" WHERE {' AND '.join(conditions)}"

            return base_query
        elif any(word in pergunta for word in ['maior', 'mais alto', 'máximo', 'melhor']):
            if table == 'estoque':
                return "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque DESC LIMIT 1"
            else:
                return "SELECT produto, zs_peso_liquido FROM faturamento ORDER BY zs_peso_liquido DESC LIMIT 1"

        # Template 5: Data mais antiga
        elif any(word in pergunta for word in ['mais antigo', 'mais antiga', 'primeiro registro', 'data inicial']):
            return f"SELECT data FROM {table} ORDER BY data ASC LIMIT 1"

        # Template 6: Listar SKUs
        elif any(word in pergunta for word in ['quais os diferentes skus', 'quais skus', 'listar skus']):
            return f"SELECT DISTINCT SKU FROM {table} ORDER BY SKU"

        # Template 7: Buscar produto por SKU específico
        elif (any(word in pergunta for word in ['qual o nome', 'nome do produto', 'qual o produto', 'produto de código', 'a qual produto', 'se refere', 'é de qual produto', 'qual produto']) and 
              any(word in pergunta for word in ['codigo', 'sku', 'código'])) or 'skus' in filters:
            # Usar filtros extraídos pelo QueryAnalyzer
            if 'skus' in filters and filters['skus']:
                sku_value = filters['skus'][0]  # Já normalizado pelo QueryAnalyzer
                return f"SELECT produto, SKU FROM {table} WHERE UPPER(SKU) = '{sku_value.upper()}' LIMIT 1"
            else:
                # Fallback: tentar extrair SKU da pergunta diretamente
                import re
                sku_match = re.search(r'sku[_]?\s*([a-zA-Z0-9]+)', pergunta, re.IGNORECASE)
                if sku_match:
                    sku_num = sku_match.group(1)
                    sku_value = f"SKU_{sku_num}"
                    return f"SELECT produto, SKU FROM {table} WHERE UPPER(SKU) = '{sku_value}' LIMIT 1"
                else:
                    return f"SELECT DISTINCT SKU FROM {table} ORDER BY SKU"

        # Template 8: Grupo de mercadoria
        elif any(word in pergunta for word in ['grupo', 'mercadoria', 'pertence']):
            if table == 'estoque':
                column_grupo = 'grupo_mercadoria'
            else:
                column_grupo = 'zs_gr_mercad'
            
            base_query = f"SELECT produto, {column_grupo} FROM {table}"
            
            # Adicionar filtros de produto se existirem
            conditions = self._build_conditions(filters, table)
            if conditions:
                base_query += f" WHERE {' AND '.join(conditions)}"
            
            return base_query + " LIMIT 1"

        # Template 9: Dados específicos de produto - ajustar para perguntas sobre quantidade
        elif 'produtos' in filters and filters['produtos'] and any(word in pergunta for word in ['quantidade', 'quantas', 'quantos', 'quanto']):
            produto = filters['produtos'][0]
            column = 'es_totalestoque' if table == 'estoque' else 'zs_peso_liquido'

            # Para perguntas sobre quantidade, fazer SUM
            base_query = f"SELECT SUM({column}) as total FROM {table} WHERE LOWER(produto) LIKE '%{produto}%'"

            # Adicionar outros filtros
            other_conditions = []
            if 'data_inicio' in filters and 'data_fim' in filters:
                other_conditions.append(f"data >= '{filters['data_inicio']}' AND data <= '{filters['data_fim']}'")

            if other_conditions:
                base_query += f" AND {' AND '.join(other_conditions)}"

            return base_query

        # Template padrão: fallback
        else:
            return f"SELECT COUNT(*) as total FROM {table}"

    def _build_conditions(self, filters: dict, table: str) -> list:
        """Constrói condições WHERE baseadas nos filtros"""
        conditions = []

        # Filtro de produtos
        if 'produtos' in filters and filters['produtos']:
            produto_conditions = []
            for produto in filters['produtos']:
                produto_conditions.append(f"LOWER(produto) LIKE '%{produto}%'")
            if produto_conditions:
                conditions.append(f"({' OR '.join(produto_conditions)})")

        # Filtro de SKUs
        if 'skus' in filters and filters['skus']:
            sku_conditions = []
            for sku in filters['skus']:
                sku_conditions.append(f"UPPER(SKU) LIKE '%{sku.upper()}%'")
            if sku_conditions:
                conditions.append(f"({' OR '.join(sku_conditions)})")

        # Filtro temporal
        if 'data_inicio' in filters and 'data_fim' in filters:
            conditions.append(f"data >= '{filters['data_inicio']}' AND data <= '{filters['data_fim']}'")

        return conditions
        
    def _generate_sql_with_ai(self, pergunta: str, contexto: str) -> str:
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
- es_totalestoque (decimal): Valor numérico em estoque
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
        prompt = f"""Você é um especialista em SQL PostgreSQL para análise de dados empresariais.

{schema_info}

PERGUNTA DO USUÁRIO: {pergunta}

INSTRUÇÕES:
- Gere APENAS a query SQL válida para PostgreSQL
- Use as tabelas "estoque" ou "faturamento" conforme apropriado
- Para perguntas sobre quantidade/estoque use SUM(es_totalestoque)
- Para perguntas sobre vendas/faturamento use SUM(zs_peso_liquido) ou SUM(giro_sku_cliente)
- Para contar registros use COUNT(*)
- Para listar produtos únicos use SELECT DISTINCT produto
- Sempre use nomes de colunas exatos
- Adicione WHERE clauses apropriados baseados na pergunta
- Use ORDER BY e LIMIT quando fizer sentido
- Responda apenas com a query SQL, sem explicações

Query SQL:"""
        
        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
            input_ids = {k: v.to(self.device) for k, v in input_ids.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **input_ids,
                    max_new_tokens=150,
                    temperature=0.1,
                    do_sample=False,
                    repetition_penalty=1.2,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0][input_ids['input_ids'].shape[1]:], skip_special_tokens=True)
            sql_query = response.strip()
            
            # Limpar resposta - remover tags HTML e texto extra
            sql_query = re.sub(r'<[^>]+>', '', sql_query).strip()
            sql_query = re.sub(r'```sql|```', '', sql_query).strip()
            sql_query = re.sub(r'^Query SQL:\s*', '', sql_query, flags=re.IGNORECASE)
            sql_query = re.sub(r'RESULTADO DA QUERY.*', '', sql_query, flags=re.IGNORECASE | re.DOTALL)
            sql_query = re.sub(r'^\s*SELECT\s+', 'SELECT ', sql_query, flags=re.IGNORECASE)
            
            # Garantir que começa com SELECT
            if not sql_query.upper().startswith('SELECT'):
                sql_query = f"SELECT {sql_query}"
            
            # Remover placeholders como ?
            sql_query = re.sub(r'\?', '', sql_query)
            
            # Limpar linhas vazias extras
            sql_query = re.sub(r'\n\s*\n', '\n', sql_query)
            
            # Se ainda tiver problemas, usar fallback
            if '<code>' in sql_query or 'RESULTADO' in sql_query or sql_query.count('SELECT') > 1:
                pergunta_lower = pergunta.lower()
                if 'quantos' in pergunta_lower and 'registros' in pergunta_lower:
                    if 'faturamento' in pergunta_lower:
                        sql_query = "SELECT COUNT(*) as total FROM faturamento"
                    else:
                        sql_query = "SELECT COUNT(*) as total FROM estoque"
                elif 'todos os produtos' in pergunta_lower or 'listar produtos' in pergunta_lower:
                    if 'faturamento' in pergunta_lower:
                        sql_query = "SELECT DISTINCT produto FROM faturamento ORDER BY produto"
                    else:
                        sql_query = "SELECT DISTINCT produto FROM estoque ORDER BY produto"
                elif 'maior' in pergunta_lower and 'es_totalestoque' in pergunta_lower:
                    sql_query = "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque DESC LIMIT 1"
                elif 'data' in pergunta_lower and ('mais antigos' in pergunta_lower or 'mais antiga' in pergunta_lower):
                    if 'faturamento' in pergunta_lower:
                        sql_query = "SELECT data FROM faturamento ORDER BY data ASC LIMIT 1"
                    else:
                        sql_query = "SELECT data FROM estoque ORDER BY data ASC LIMIT 1"
                elif 'quais' in pergunta_lower and 'skus' in pergunta_lower:
                    if 'faturamento' in pergunta_lower:
                        sql_query = "SELECT DISTINCT SKU FROM faturamento ORDER BY SKU"
                    else:
                        sql_query = "SELECT DISTINCT SKU FROM estoque ORDER BY SKU"
                else:
                    # Fallback genérico
                    if 'faturamento' in pergunta_lower or 'vendas' in pergunta_lower:
                        sql_query = "SELECT SUM(zs_peso_liquido) as total FROM faturamento"
                    else:
                        sql_query = "SELECT SUM(es_totalestoque) as total FROM estoque"
            
            print(f"[SQL AI] Query final: {sql_query}")
            return sql_query
            
        except Exception as e:
            print(f"[ERRO SQL AI] {e}")
            # Fallback simples
            pergunta_lower = pergunta.lower()
            if 'estoque' in pergunta_lower:
                return "SELECT SUM(es_totalestoque) as total FROM estoque"
            else:
                return "SELECT SUM(zs_peso_liquido) as total FROM faturamento"
    
    def process_input(self, pergunta: str, contexto: str, analise: dict = None) -> str:
        try:
            sql_query = self.generate_sql(pergunta, contexto, analise=analise)
            print(f"\nSQL gerada: {sql_query}")
            sql_result = execute_query(sql_query)
            print(f"Resultado SQL: {sql_result}")
            
            # Para perguntas factuais simples, usar resposta direta sem AI
            pergunta_lower = pergunta.lower()
            query_type = analise.get("type", "") if analise else ""
            is_factual_question = (
                ('quantos' in pergunta_lower and 'registros' in pergunta_lower) or
                ('qual é a data' in pergunta_lower and 'mais antig' in pergunta_lower) or
                ('qual produto tem maior' in pergunta_lower) or
                ('quais' in pergunta_lower and 'skus' in pergunta_lower) or
                ('todos os produtos' in pergunta_lower) or
                ('informe o nome' in pergunta_lower and 'produtos' in pergunta_lower) or
                (('quantas' in pergunta_lower or 'quantos' in pergunta_lower) and analise and analise.get('filters', {}).get('produtos')) or
                ('qual o nome' in pergunta_lower and 'produto' in pergunta_lower and ('codigo' in pergunta_lower or 'sku' in pergunta_lower)) or
                ('a que grupo' in pergunta_lower and 'mercadoria' in pergunta_lower) or
                ('pertence' in pergunta_lower and 'mercadoria' in pergunta_lower) or
                ('faturamento' in pergunta_lower and analise and analise.get('filters', {}).get('mes')) or  # Faturamento com período específico
                (('qual' in pergunta_lower and 'produto' in pergunta_lower) or ('produto' in pergunta_lower and 'sku' in pergunta_lower)) or  # Perguntas sobre produto por SKU
                query_type == "sku_lookup"  # Novo tipo para perguntas sobre produto por SKU
            )
            
            if is_factual_question:
                final_response = self._format_fallback_response(pergunta, sql_result, analise.get("filters", {}) if analise else {})
            else:
                final_response = self._generate_conversational_response(pergunta, sql_result, contexto, analise)
            
            return final_response
        except Exception as e:
            print(f"Erro: {str(e)}")
            return f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}"
    
    def _generate_conversational_response(self, pergunta: str, sql_result: list, contexto: str, analise: dict = None) -> str:
        if not sql_result:
            return "Não encontrei dados relevantes para sua pergunta nos registros disponíveis."

        dados_formatados = self._format_sql_for_ai(sql_result, analise.get("filters", {}) if analise else {})

        prompt = f"""Você é um assistente corporativo especializado em análise de dados de estoque e faturamento.

Pergunta do usuário: {pergunta}

Dados encontrados no banco: {dados_formatados}

INSTRUÇÕES:
- Responda de forma educada, profissional e conversacional em português
- Mantenha um tom corporativo apropriado para ambiente empresarial
- Mencione os números exatos encontrados com formatação adequada
- Seja útil, claro e objetivo
- Use expressões como "conforme nossos registros", "segundo os dados", "posso informar que"
- Se não houver dados suficientes, explique claramente e ofereça alternativas
- Mantenha a resposta concisa mas informativa

Resposta:"""

        try:
            input_ids = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
            input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **input_ids,
                    max_new_tokens=200,
                    temperature=0.3,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(outputs[0][input_ids['input_ids'].shape[1]:], skip_special_tokens=True)
            response = response.strip()

            # Limpar resposta
            response = re.sub(r'^Resposta:\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'<[^>]+>', '', response).strip()

            if response and len(response) > 10:
                return response
            else:
                return self._format_fallback_response(pergunta, sql_result, analise.get("filters", {}) if analise else {})

        except Exception as e:
            print(f"[ERRO Conversacional AI] {e}")
            return self._format_fallback_response(pergunta, sql_result, analise.get("filters", {}) if analise else {})

    
    def _format_fallback_response(self, pergunta: str, sql_result: list, filters: dict) -> str:
        pergunta_lower = pergunta.lower()

        # Detecção específica para perguntas factuais (ajustada para variações)
        if 'quantos' in pergunta_lower and 'registros' in pergunta_lower:
            if sql_result and 'total' in sql_result[0]:
                total = sql_result[0]['total']
                # Para contagem de registros, sempre formatar como inteiro
                if isinstance(total, Decimal):
                    total = int(total)
                return f"Segundo nossos registros, a tabela possui {total} entradas cadastradas."

        elif 'todos os produtos' in pergunta_lower or 'listar produtos' in pergunta_lower or ('informe o nome' in pergunta_lower and 'produtos' in pergunta_lower):
            if sql_result:
                produtos = [row['produto'] for row in sql_result]
                return f"Os produtos disponíveis em nosso sistema são: {', '.join(produtos)}."

        elif 'data' in pergunta_lower and ('mais antigos' in pergunta_lower or 'mais antiga' in pergunta_lower or 'registros mais antigos' in pergunta_lower):
            if sql_result and 'data' in sql_result[0]:
                return f"O registro mais antigo em nossa base de dados é de {sql_result[0]['data']}."

        elif 'qual produto tem maior' in pergunta_lower and 'es_totalestoque' in pergunta_lower:
            if sql_result and 'produto' in sql_result[0] and 'es_totalestoque' in sql_result[0]:
                produto = sql_result[0]['produto']
                quantidade = float(sql_result[0]['es_totalestoque'])
                return f"O produto com maior volume em estoque é {produto}, com {quantidade:,.2f} unidades disponíveis."

        elif 'quais os diferentes skus' in pergunta_lower or 'quais skus' in pergunta_lower:
            if sql_result:
                skus = [row['sku'] for row in sql_result]
                return f"Os códigos SKU disponíveis são: {', '.join(skus)}."

        # Detecção específica para perguntas sobre quantidade de produtos específicos
        elif ('quantas' in pergunta_lower or 'quantos' in pergunta_lower) and 'produtos' in filters and filters['produtos']:
            if sql_result and 'total' in sql_result[0]:
                total = sql_result[0]['total']
                produto = filters['produtos'][0]
                # Para contagem de produtos específicos, formatar como inteiro
                if isinstance(total, Decimal):
                    total = int(total)
                return f"Conforme nossos registros, encontramos {total} entradas para o produto {produto}."

        # Detecção para perguntas sobre nome de produto por SKU
        elif ('qual o nome' in pergunta_lower and 'produto' in pergunta_lower and ('codigo' in pergunta_lower or 'sku' in pergunta_lower)) or \
             (('qual o produto' in pergunta_lower or 'qual produto' in pergunta_lower or 'a qual produto' in pergunta_lower or 'se refere' in pergunta_lower) and 'sku' in pergunta_lower) or \
             ('produto' in pergunta_lower and 'sku' in pergunta_lower and ('qual' in pergunta_lower or 'é o' in pergunta_lower or 'é de qual' in pergunta_lower)):
            if sql_result and len(sql_result) > 0:
                produto = sql_result[0].get('produto', 'Não encontrado')
                sku = sql_result[0].get('sku', 'N/A')
                if produto != 'Não encontrado':
                    return f"O produto identificado pelo código SKU {sku} é {produto}."
                else:
                    return "Desculpe, não foi possível localizar um produto com o código SKU informado."
            else:
                return "Desculpe, não foi possível localizar um produto com o código SKU informado."

        # Detecção para perguntas sobre grupo de mercadoria
        elif ('a que grupo' in pergunta_lower and 'mercadoria' in pergunta_lower) or ('pertence' in pergunta_lower and 'mercadoria' in pergunta_lower):
            if sql_result and len(sql_result) > 0:
                produto = sql_result[0].get('produto', 'Produto não identificado')
                grupo = sql_result[0].get('grupo_mercadoria', sql_result[0].get('zs_gr_mercad', 'Grupo não encontrado'))
                return f"O produto {produto} está classificado no grupo de mercadoria: {grupo}."
            else:
                return "Não foi possível determinar o grupo de mercadoria para o produto solicitado."

        # Fallback original para outras perguntas
        if 'produtos' in filters and filters['produtos']:
            produto = filters['produtos'][0]
            if sql_result and len(sql_result) > 0:
                total = sql_result[0].get('total', 0)
                if isinstance(total, Decimal):
                    total = float(total)
                return f"Atualmente mantemos {total:,.2f} unidades do produto {produto} em nosso estoque."
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
                    periodo = f" no mês de {mes_nome} de {filters['ano']}"
                return f"O faturamento registrado{periodo} totalizou R$ {total:,.2f}."
        if sql_result and len(sql_result) > 0 and 'total' in sql_result[0]:
            total = sql_result[0]['total']
            if isinstance(total, Decimal):
                total = float(total)
            unidade = "R$" if 'faturamento' in pergunta_lower else "unidades"
            return f"O valor identificado foi de {unidade} {total:,.2f}."
        return "Não foram encontrados resultados para esta consulta em nossa base de dados."
    
    def _format_sql_for_ai(self, sql_result: list, filters: dict) -> str:
        if not sql_result:
            return "Nenhum dado encontrado."
        formatted = ""
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
        if len(sql_result) == 1 and 'total' in sql_result[0]:
            total = sql_result[0]['total']
            if isinstance(total, Decimal):
                total = float(total)
            formatted += f"Valor total encontrado: {total:,.2f}"
        else:
            formatted += f"Registros encontrados: {len(sql_result)}\n"
            for i, row in enumerate(sql_result[:5]):
                formatted += f"Registro {i+1}: {', '.join([f'{k}: {v}' for k, v in row.items()])}\n"
        return formatted

if __name__ == "__main__":
    agent = AgentService()
    pergunta = input("Digite sua pergunta: ")
    print(agent.processar_pergunta_simples(pergunta))