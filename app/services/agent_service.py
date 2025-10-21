import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from app.db.neon_db import execute_query
import re

load_dotenv()

class AgentService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("AgentService using device:", self.device)
        
        # Usar mesmo modelo do BoletimService para consistência
        if self.device.type == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-2-2b-it",  
                token=HG_TOKEN,
                device_map="auto",
                dtype=torch.bfloat16,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-2-2b-it",  
                low_cpu_mem_usage=True,
            )
            self.model.to(self.device, dtype=torch.float32)

        self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-2b-it") 
        
        # Cache para otimização
        self._cache = {}
        self._cache_max_size = 100
    
    def processar_pergunta_simples(self, pergunta: str) -> str:
        """Processa pergunta sem contexto adicional - só IA pura"""
        if not pergunta or not pergunta.strip():
            return "Por favor, faça uma pergunta válida."
        
        # Verificar cache
        cache_key = f"simple_{hash(pergunta)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"""Você é um assistende de análise de dados empresariais. O usuário fez um questionamento:
        
        PERGUNTA DO USUÁRIO: {pergunta}

        Responda de forma clara, objetiva e profissional em português.
        Se não for uma pergunta rotorne: Faça uma pergunta válida.
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
        """Gera resposta usando o modelo de IA"""
        input_ids = self.tokenizer(prompt, return_tensors="pt")
        input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **input_ids, 
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        output_str = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Limpar prompt da resposta
        if prompt in output_str:
            response = output_str.replace(prompt, "").strip()
        else:
            response = output_str.strip()
        
        return response if response else "Não foi possível gerar uma resposta adequada."
    
    def clear_cache(self):
        """Limpa o cache de respostas"""
        self._cache.clear()
    
    def generate_sql(self, pergunta: str, contexto: str) -> str:
        """Gera query SQL baseada na pergunta e contexto"""
        
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
        
        # Fallbacks específicos para queries comuns
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
        # Novo: detectar pergunta dupla sobre produtos diferentes
        elif ('produtos diferentes' in pergunta_lower or 'quais são' in pergunta_lower) and 'quantos' in pergunta_lower:
            if 'faturamento' in pergunta_lower:
                sql_query = "SELECT DISTINCT produto FROM faturamento ORDER BY produto"
            else:
                sql_query = "SELECT DISTINCT produto FROM estoque ORDER BY produto"
        # Novo: detectar pergunta sobre data mais antiga
        elif 'data' in pergunta_lower and ('mais antigos' in pergunta_lower or 'mais antiga' in pergunta_lower):
            if 'faturamento' in pergunta_lower:
                sql_query = "SELECT data FROM faturamento ORDER BY data ASC LIMIT 1"
            else:
                sql_query = "SELECT data FROM estoque ORDER BY data ASC LIMIT 1"
        
        return sql_query.strip()
    
    def format_sql_response(self, pergunta: str, sql_result: list) -> str:
        """Formata resultado SQL de forma factual, sem interpretação"""
        if not sql_result:
            return "Nenhum resultado encontrado para esta consulta."
        
        pergunta_lower = pergunta.lower()
        
        # Respostas factuais específicas
        if 'maior' in pergunta_lower and 'es_totalestoque' in pergunta_lower:
            if sql_result and len(sql_result) > 0:
                item = sql_result[0]
                produto = item.get('produto', 'N/A')
                valor = item.get('es_totalestoque', 0)
                return f"Produto: {produto}, es_totalestoque: {valor}"
        
        elif 'todos os produtos' in pergunta_lower or 'listar produtos' in pergunta_lower:
            produtos = [item.get('produto', 'N/A') for item in sql_result]
            return f"Produtos encontrados: {', '.join(produtos[:10])}" + ("..." if len(produtos) > 10 else "")
        
        # Novo: lidar com pergunta dupla sobre produtos diferentes
        elif ('produtos diferentes' in pergunta_lower or 'quais são' in pergunta_lower) and 'quantos' in pergunta_lower:
            produtos = [item.get('produto', 'N/A') for item in sql_result]
            total = len(produtos)
            return f"Total: {total} produtos diferentes. São eles: {', '.join(produtos)}"
        
        elif 'quantos' in pergunta_lower:
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
    
    def process_input(self, pergunta: str, contexto: str) -> str:
        """Método principal que integra SQL + IA"""
        try:
            # 1. Gerar SQL
            sql_query = self.generate_sql(pergunta, contexto)
            print(f"\nSQL gerada: {sql_query}")
            
            # 2. Executar SQL
            sql_result = execute_query(sql_query)
            print(f"Resultado: {sql_result}")
            
            # 3. Formatar resposta
            final_response = self.format_sql_response(pergunta, sql_result)
            
            return final_response
            
        except Exception as e:
            print(f"Erro: {str(e)}")
            return f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}"

if __name__ == "__main__":
    agent = AgentService()
    pergunta = input("Digite sua pergunta: ")
    print(agent.processar_pergunta_simples(pergunta))
