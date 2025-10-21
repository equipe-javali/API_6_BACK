import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from db.neon_db import execute_query
import re

load_dotenv()

class AgentService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("AgentService using device:", self.device)
        
        # Usar mesmo modelo do BoletimService para consistência
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
        """Gera query SQL baseada em mapeamento seguro (sem IA)"""
        
        pergunta_lower = pergunta.lower()
        
        # Mapeamento direto de palavras-chave para queries seguras
        queries_seguras = {
            # Perguntas sobre produtos
            'quantos produtos': "SELECT COUNT(DISTINCT produto) as total_produtos FROM estoque",
            'listar produtos': "SELECT DISTINCT produto FROM estoque ORDER BY produto LIMIT 20",
            'produtos diferentes': "SELECT DISTINCT produto FROM estoque ORDER BY produto",
            'quais produtos': "SELECT DISTINCT produto FROM estoque ORDER BY produto LIMIT 20",
            
            # Perguntas sobre estoque
            'maior es_totalestoque': "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque DESC LIMIT 1",
            'maior estoque': "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque DESC LIMIT 1",
            'menor estoque': "SELECT produto, es_totalestoque FROM estoque ORDER BY es_totalestoque ASC LIMIT 1",
            'estoque total': "SELECT SUM(es_totalestoque) as total FROM estoque",
            'total estoque': "SELECT SUM(es_totalestoque) as total FROM estoque",
            
            # Perguntas sobre faturamento
            'quantos registros faturamento': "SELECT COUNT(*) as total_registros FROM faturamento",
            'quantos faturamentos': "SELECT COUNT(*) as total_registros FROM faturamento",
            'registros faturamento': "SELECT COUNT(*) as total_registros FROM faturamento",
            
            # Perguntas sobre centros
            'centros': "SELECT DISTINCT es_centro FROM estoque LIMIT 10",
            'quantos centros': "SELECT COUNT(DISTINCT es_centro) as total FROM estoque",
            
            # Perguntas sobre SKUs
            'quantos skus': "SELECT COUNT(DISTINCT sku) as total FROM estoque",
            'skus': "SELECT DISTINCT sku FROM estoque LIMIT 20",
            
            # Perguntas sobre data
            'data mais antiga': "SELECT MIN(data) as data_mais_antiga FROM estoque",
            'data mais recente': "SELECT MAX(data) as data_mais_recente FROM estoque",
        }
        
        # Procurar por match nas palavras-chave
        for palavra_chave, query_sql in queries_seguras.items():
            if palavra_chave in pergunta_lower:
                print(f"[generate_sql] Match encontrado: '{palavra_chave}'")
                return query_sql
        
        # Fallback: query padrão segura
        print(f"[generate_sql] Nenhum match, usando fallback")
        return "SELECT DISTINCT produto FROM estoque LIMIT 10"
    
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
