from typing import Dict, List, Any
from db.neon_db import NeonDB

class ContextService:
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos
    
    def get_estoque_context(self, user_id: int, query_type: str = "general") -> Dict[str, Any]:
        """Busca dados de estoque relevantes para o contexto"""
        with NeonDB() as db:
            # Dados gerais de estoque
            estoque_data = db.fetchall("""
                SELECT data, cod_cliente, produto, es_totalestoque, SKU, dias_em_estoque
                FROM estoque 
                ORDER BY data DESC 
                LIMIT 100
            """)
            
            return {
                "tipo": "estoque",
                "total_registros": len(estoque_data),
                "dados": estoque_data,
                "resumo": self._generate_estoque_summary(estoque_data)
            }
    
    def get_faturamento_context(self, user_id: int, query_type: str = "general") -> Dict[str, Any]:
        """Busca dados de faturamento relevantes para o contexto"""
        with NeonDB() as db:
            faturamento_data = db.fetchall("""
                SELECT data, cod_cliente, produto, zs_peso_liquido, giro_sku_cliente, SKU
                FROM faturamento 
                ORDER BY data DESC 
                LIMIT 100
            """)
            
            return {
                "tipo": "faturamento",
                "total_registros": len(faturamento_data),
                "dados": faturamento_data,
                "resumo": self._generate_faturamento_summary(faturamento_data)
            }
    
    def get_combined_context(self, user_id: int, query_hint: str = "") -> str:
        """Gera contexto combinado formatado para o prompt do agente"""
        estoque_ctx = self.get_estoque_context(user_id)
        faturamento_ctx = self.get_faturamento_context(user_id)
        
        context_text = f"""
        CONTEXTO DOS DADOS:
        
        ESTOQUE:
        - Total de registros: {estoque_ctx['total_registros']}
        - Resumo: {estoque_ctx['resumo']}
        
        FATURAMENTO:
        - Total de registros: {faturamento_ctx['total_registros']}
        - Resumo: {faturamento_ctx['resumo']}
        
        Use estes dados para responder perguntas sobre estoque, vendas, produtos e análises de negócio.
        """
        
        return context_text.strip()
    
    def _generate_estoque_summary(self, data: List[tuple]) -> str:
        """Gera resumo dos dados de estoque"""
        if not data:
            return "Nenhum dado de estoque disponível"
        
        total_estoque = sum(float(row[3] or 0) for row in data)
        produtos_unicos = len(set(row[2] for row in data if row[2]))
        
        return f"Total em estoque: {total_estoque:.2f}, Produtos únicos: {produtos_unicos}"
    
    def _generate_faturamento_summary(self, data: List[tuple]) -> str:
        """Gera resumo dos dados de faturamento"""
        if not data:
            return "Nenhum dado de faturamento disponível"
        
        total_peso = sum(float(row[3] or 0) for row in data)
        produtos_unicos = len(set(row[2] for row in data if row[2]))
        
        return f"Total peso líquido: {total_peso:.2f}, Produtos únicos: {produtos_unicos}"
    
    def generate_context(self, focus_areas: list) -> str:
        """Gera contexto factual simples"""
        
        return """
DADOS DISPONÍVEIS:

TABELA ESTOQUE: dados sobre produtos em estoque
- es_totalestoque: valores numéricos
- produto: tipos como Bobina, Rolo, Chapa, Tira
- SKU: identificadores únicos

TABELA FATURAMENTO: dados de vendas/faturamento  
- zs_peso_liquido: valores numéricos de peso
- zs_cidade, zs_uf: localização
- produto: tipos de produtos vendidos

Use SQL para consultar dados factuais exatos.
"""