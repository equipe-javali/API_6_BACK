
import re
from typing import Dict, List, Any

class QueryAnalyzer:
    def __init__(self):
        # Palavras-chave para identificar tipo de consulta
        self.estoque_keywords = [
            'estoque', 'produto', 'sku', 'armazenado', 'disponível', 
            'quantidade', 'aging', 'dias em estoque'
        ]
        
        self.faturamento_keywords = [
            'faturamento', 'vendas', 'venda', 'cliente', 'peso', 
            'giro', 'receita', 'faturado'
        ]
        
        self.analise_keywords = [
            'análise', 'comparar', 'tendência', 'crescimento', 
            'redução', 'melhor', 'pior', 'média'
        ]
    
    def analyze_query(self, pergunta: str) -> Dict[str, Any]:
        """Analisa pergunta e determina que tipo de contexto buscar"""
        pergunta_lower = pergunta.lower()
        
        # Contar ocorrências de palavras-chave
        estoque_score = sum(1 for keyword in self.estoque_keywords 
                          if keyword in pergunta_lower)
        faturamento_score = sum(1 for keyword in self.faturamento_keywords 
                              if keyword in pergunta_lower)
        analise_score = sum(1 for keyword in self.analise_keywords 
                           if keyword in pergunta_lower)
        
        if estoque_score + faturamento_score + analise_score == 0:
            return
        
        # Determinar foco principal
        query_focus = []
        if estoque_score > 0:
            query_focus.append("estoque")
        if faturamento_score > 0:
            query_focus.append("faturamento")
        
        # Se não identificou foco específico, incluir ambos
        if not query_focus:
            query_focus = ["estoque", "faturamento"]
        
        # Determinar tipo de análise
        if analise_score > 0:
            query_type = "analytical"
        elif any(word in pergunta_lower for word in ['quanto', 'quantos', 'qual']):
            query_type = "quantitative"
        else:
            query_type = "general"
        
        # Detectar filtros específicos
        filters = self._extract_filters(pergunta_lower)
        
        return {
            "focus": query_focus,
            "type": query_type,
            "filters": filters,
            "complexity_score": estoque_score + faturamento_score + analise_score,
            "requires_detailed_data": analise_score > 0 or "detalh" in pergunta_lower
        }
    
    def _extract_filters(self, pergunta: str) -> Dict[str, Any]:
        """Extrai filtros específicos da pergunta"""
        filters = {}
        
        # Detectar SKUs específicos
        sku_pattern = r'sku[_\s]*(\w+)'
        sku_matches = re.findall(sku_pattern, pergunta)
        if sku_matches:
            filters['skus'] = sku_matches
        
        # Detectar produtos específicos
        if 'produto' in pergunta:
            # Tentar extrair nome do produto (implementação básica)
            produto_pattern = r'produto\s+(\w+)'
            produto_matches = re.findall(produto_pattern, pergunta)
            if produto_matches:
                filters['produtos'] = produto_matches
        
        # Detectar períodos de tempo
        if any(word in pergunta for word in ['mês', 'semana', 'ano', 'período']):
            filters['temporal'] = True
        
        return filters