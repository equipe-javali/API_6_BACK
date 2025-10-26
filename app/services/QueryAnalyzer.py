import re
from typing import Dict, List, Any, Set
from datetime import datetime
from difflib import get_close_matches  # Para correção ortográfica
import nltk
from nltk.stem import RSLPStemmer  # Stemmer específico para português
from nltk.corpus import stopwords

# Baixar recursos necessários (executar uma vez)
try:
    nltk.download('rslp', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    print(f"Aviso: Erro ao baixar recursos NLTK: {e}")

class QueryAnalyzer:
    def __init__(self):
        # Palavras-chave para identificar tipo de consulta (expandidas com sinônimos e plurais do primeiro código, mas mantendo simplicidade)
        self.estoque_keywords = [
            'estoque', 'estoques', 'produto', 'produtos', 'sku', 'skus', 'armazenado', 'armazenados', 
            'disponível', 'disponíveis', 'quantidade', 'quantidades', 'aging', 'dias em estoque', 
            'inventário', 'inventários', 'stock', 'stocks', 'bobina', 'bobinas', 'chapa', 'chapas', 
            'rolo', 'rolos', 'tira', 'tiras', 'laminado', 'laminados', 'aço', 'aços', 'registros', 'registro', 'data'  # Mantido 'data' para detectar perguntas sobre datas
        ]
        
        self.faturamento_keywords = [
            'faturamento', 'faturamentos', 'vendas', 'venda', 'cliente', 'clientes', 'peso', 'pesos', 
            'giro', 'giros', 'receita', 'receitas', 'faturado', 'faturados', 'lucro', 'lucros', 
            'volume', 'volumes'  # Removido 'registro' e 'data' para evitar foco ambíguo
        ]
        
        
        self.analise_keywords = [
            'análise', 'análises', 'comparar', 'comparação', 'tendência', 'tendências', 'crescimento', 
            'crescimentos', 'redução', 'reduções', 'melhor', 'melhores', 'pior', 'piores', 'média', 
            'médias', 'estatística', 'estatísticas'
        ]
        
        # Mapeamento de meses para números (do primeiro código)
        self.meses = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
            'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
        }
        # Variações comuns (abreviaturas)
        self.meses_variacoes = {
            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
        }
        
        # Sinônimos para produtos (do primeiro código)
        self.produto_sinonimos = {
            'bobina': ['bobina', 'bobinas', 'coil', 'coils'],
            'chapa': ['chapa', 'chapas', 'sheet', 'sheets', 'placa', 'placas'],
            'rolo': ['rolo', 'rolos', 'roll', 'rolls'],
            'tira': ['tira', 'tiras', 'strip', 'strips', 'barra', 'barras'],
            'laminado': ['laminado', 'laminados', 'laminated', 'aço laminado', 'aços laminados'],
            'aço': ['aço', 'aços', 'steel', 'steels', 'metal', 'metals']
        }
        
        # Lista de produtos conhecidos para correção ortográfica
        self.produtos_conhecidos = ['bobina', 'chapa', 'rolo', 'tira', 'laminado', 'aço']
        
        # Inicializar stemmer e stopwords
        try:
            self.stemmer = RSLPStemmer()
            self.stop_words = set(stopwords.words('portuguese'))
        except Exception as e:
            print(f"Aviso: Erro ao inicializar NLTK: {e}. Usando fallbacks.")
            self.stemmer = None
            self.stop_words = set()

    def analyze_query(self, pergunta: str) -> Dict[str, Any]:
        """Analisa pergunta e determina que tipo de contexto buscar (mescla otimizada)"""
        pergunta_lower = pergunta.lower()
        
        # Contar ocorrências de palavras-chave no texto original (como no segundo código, para evitar normalização excessiva)
        estoque_score = sum(1 for keyword in self.estoque_keywords 
                          if keyword in pergunta_lower)
        faturamento_score = sum(1 for keyword in self.faturamento_keywords 
                              if keyword in pergunta_lower)
        analise_score = sum(1 for keyword in self.analise_keywords 
                           if keyword in pergunta_lower)
        
        # Se score == 0, retornar None (como no segundo código, para compatibilidade com test_full_flow.py)
        if estoque_score + faturamento_score + analise_score == 0:
            return None
        
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
        elif any(word in pergunta_lower for word in ['quanto', 'quantos', 'quantas', 'qual', 'quais']):
            # Verificar se é pergunta sobre produto específico por SKU
            if 'sku' in pergunta_lower and any(word in pergunta_lower for word in ['produto', 'qual', 'código']):
                query_type = "sku_lookup"
            else:
                query_type = "quantitative"
        else:
            query_type = "general"
        
        # Detectar filtros específicos (usando PLN avançada do primeiro código)
        filters = self._extract_filters(pergunta_lower)
        
        return {
            "focus": query_focus,
            "type": query_type,
            "filters": filters,
            "complexity_score": estoque_score + faturamento_score + analise_score,
            "requires_detailed_data": analise_score > 0 or "detalh" in pergunta_lower
        }

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto com correção ortográfica, remoção de stopwords e stemming/lemmatização avançada (do primeiro código)"""
        # Remover pontuação
        text = re.sub(r'[^\w\s]', '', text)
        # Converter para minúsculas
        text = text.lower()
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            if word not in self.stop_words:
                # Correção ortográfica para produtos
                if word in self.produtos_conhecidos:
                    corrected_words.append(word)
                else:
                    # Tentar correção ortográfica
                    matches = get_close_matches(word, self.produtos_conhecidos, n=1, cutoff=0.8)
                    if matches:
                        corrected_words.append(matches[0])
                        print(f"[PLN] Corrigido '{word}' para '{matches[0]}'")
                    else:
                        # Aplicar stemming/lemmatização
                        stemmed = self._stem_word(word)
                        corrected_words.append(stemmed)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)

    def _stem_word(self, word: str) -> str:
        """Stemming/lemmatização usando RSLPStemmer ou fallback básico (do primeiro código)"""
        if self.stemmer:
            try:
                return self.stemmer.stem(word)
            except:
                pass
        # Fallback para stemming básico (remover sufixos comuns)
        sufixos = ['s', 'es', 'a', 'as', 'o', 'os', 'ção', 'ções', 'mente']
        for sufixo in sufixos:
            if word.endswith(sufixo) and len(word) > len(sufixo) + 1:
                return word[:-len(sufixo)]
        return word

    def _extract_filters(self, pergunta: str) -> Dict[str, Any]:
        """Extrai filtros específicos da pergunta, incluindo datas/meses/anos e produtos com PLN aprimorado (do primeiro código)"""
        filters = {}
        pergunta_lower = pergunta.lower()
        
        print(f"[PLN DEBUG] Extraindo filtros de pergunta: '{pergunta}'")
        
        # 1. Detecção de produtos com PLN avançado (sinônimos + plurais)
        produtos_detectados: Set[str] = set()
        
        # Verificar sinônimos diretos
        for produto_base, sinonimos in self.produto_sinonimos.items():
            for sinonimo in sinonimos:
                if sinonimo in pergunta_lower:
                    produtos_detectados.add(produto_base)
                    print(f"[PLN DEBUG] Produto detectado (sinônimo): '{sinonimo}' -> '{produto_base}'")
        
        # Verificar stemming
        pergunta_normalizada = self._normalize_text(pergunta)
        words = pergunta_normalizada.split()
        
        for produto in self.produtos_conhecidos:
            stemmed_produto = self._stem_word(produto)
            if stemmed_produto in words:
                produtos_detectados.add(produto)
                print(f"[PLN DEBUG] Produto detectado (stemming): '{produto}' via stemming")
        
        if produtos_detectados:
            filters['produtos'] = list(produtos_detectados)
        
        # 2. Detecção de SKUs aprimorada (ajustado para capturar SKUs válidos com pelo menos 1 caracter após SKU)
        sku_pattern = r'\bsku[_]?\s*([a-zA-Z0-9]+)\b'
        sku_matches = re.findall(sku_pattern, pergunta_lower, re.IGNORECASE)
        if sku_matches:
            # Normalizar SKUs para formato SKU_X
            normalized_skus = []
            for sku in sku_matches:
                if not sku.startswith('_'):
                    normalized_skus.append(f"SKU_{sku}")
                else:
                    normalized_skus.append(f"SKU{sku}")
            filters['skus'] = normalized_skus
            print(f"[PLN DEBUG] SKUs detectados: {normalized_skus}")
        
        # 3. Detecção de datas aprimorada com padrões regex robustos
        # Padrões para datas: "abril de 2024", "abril 2024", "04/2024", "2024/04", etc.
        mes_ano_patterns = [
            r'(\w+)\s+de\s+(\d{4})',  # abril de 2024
            r'(\w+)\s+(\d{4})',       # abril 2024
            r'(\d{1,2})/(\d{4})',     # 04/2024
            r'(\d{4})/(\d{1,2})',     # 2024/04
        ]
        
        for pattern in mes_ano_patterns:
            match = re.search(pattern, pergunta_lower)
            if match:
                parte1, parte2 = match.groups()
                
                # Tentar identificar mês e ano
                mes_num = None
                ano = None
                
                # Verificar se parte1 é mês
                for mes_nome, num in self.meses.items():
                    if mes_nome in parte1.lower():
                        mes_num = num
                        ano = int(parte2)
                        break
                
                # Verificar se parte1 é número (mês)
                try:
                    mes_cand = int(parte1)
                    if 1 <= mes_cand <= 12:
                        mes_num = mes_cand
                        ano = int(parte2)
                except:
                    pass
                
                # Verificar se parte2 é mês
                if not mes_num:
                    for mes_nome, num in self.meses.items():
                        if mes_nome in parte2.lower():
                            mes_num = num
                            ano = int(parte1)
                            break
                
                if mes_num and ano:
                    # Criar período
                    try:
                        data_inicio = datetime(ano, mes_num, 1)
                        if mes_num == 12:
                            data_fim = datetime(ano + 1, 1, 1)
                        else:
                            data_fim = datetime(ano, mes_num + 1, 1)
                        
                        filters['data_inicio'] = data_inicio.strftime('%Y-%m-%d')
                        filters['data_fim'] = data_fim.strftime('%Y-%m-%d')
                        filters['mes'] = mes_num
                        filters['ano'] = ano
                        print(f"[PLN DEBUG] Período detectado: {mes_num}/{ano} ({filters['data_inicio']} a {filters['data_fim']})")
                    except ValueError as e:
                        print(f"[PLN DEBUG] Erro ao criar período: {e}")
                break
        
        # 4. Detecção de períodos temporais
        if any(word in words for word in ['mes', 'mês', 'seman', 'ano', 'period']):
            filters['temporal'] = True
        
        print(f"[PLN DEBUG] Filtros extraídos finais: {filters}")
        return filters

