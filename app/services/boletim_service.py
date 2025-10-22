import re
import random
from datetime import datetime, timedelta
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

from models.dados_boletim_model import DadosBoletimModel



class BoletimService:
    def __init__(self):
        # Definindo seed fixa para reprodutibilidade
        seed_value = 42
        random.seed(seed_value)
        torch.manual_seed(seed_value)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed_value)
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("BoletimService using device:", self.device)

        if self.device.type == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-3-1b-pt",
                device_map="auto",
                dtype=torch.bfloat16,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-3-1b-pt",
                low_cpu_mem_usage=True,
            )
            self.model.to(self.device, dtype=torch.float32)
            
        # Ativando modo de avaliação para desativar dropout e garantir consistência
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-1b-pt")

    def _gerar_periodo_boletim(self) -> tuple[str, str]:
        """Gera o período do boletim (últimas 52 semanas)"""
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(weeks=52)
        return data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y")

    def _formatar_dados_estruturados(self, dados: DadosBoletimModel) -> str:
        """Formata os dados de forma estruturada para facilitar análise"""
        data_inicio, data_fim = self._gerar_periodo_boletim()
              
        skus_alto = ", ".join(dados.skus_alto_giro_sem_estoque) if dados.skus_alto_giro_sem_estoque else "Nenhum"
        itens_repor = ", ".join(dados.itens_a_repor) if dados.itens_a_repor else "Nenhum"

        prob_sku1 = getattr(dados, "probabilidade_desabastecimento_sku1", None)
        prob_text = f"• Probabilidade de desabastecimento do SKU_1 em <2 semanas: {prob_sku1}" if prob_sku1 is not None else ""
        
        return f"""
📊 INDICADORES DE ESTOQUE E FATURAMENTO
Período Analisado: {data_inicio} a {data_fim} (últimas 52 semanas)

1. CONSUMO E MOVIMENTAÇÃO
   • Estoque Total Consumido: {dados.qtd_estoque_consumido_ton} toneladas
   • Frequência de Compra: {dados.freq_compra} meses com pedidos

2. AGING DE ESTOQUE (em semanas)
   • Mínimo: {dados.valor_aging_min} semanas
   • Médio: {dados.valor_aging_avg} semanas
   • Máximo: {dados.valor_aging_max} semanas

3. ANÁLISE POR SKU
   • Clientes ativos no SKU_1: {dados.qtd_consomem_sku1}
   • SKUs de alto giro SEM estoque: {skus_alto}
   • Itens que necessitam reposição: {itens_repor}

4. ALERTAS CRÍTICOS
   • Risco de desabastecimento SKU_1: {dados.risco_desabastecimento_sku1}
{prob_text}
"""

    def _gerar_analise_baseada_regras(self, dados: DadosBoletimModel) -> str:
        """Gera análise baseada em regras quando a IA falha"""
        analise = []
        
        # Análise de consumo
        if dados.qtd_estoque_consumido_ton > 100:
            analise.append(f"O consumo de estoque no período foi elevado ({dados.qtd_estoque_consumido_ton} toneladas), indicando alta demanda operacional. ")
        else:
            analise.append(f"O consumo de estoque foi moderado ({dados.qtd_estoque_consumido_ton} toneladas). ")
        
        # Análise de aging
        if dados.valor_aging_avg > 8:
            analise.append(f"O aging médio de {dados.valor_aging_avg} semanas sugere estoque com baixa rotatividade, podendo impactar o capital de giro. ")
        elif dados.valor_aging_avg < 4:
            analise.append(f"O aging médio de {dados.valor_aging_avg} semanas indica boa rotatividade de estoque. ")
        
        # Análise de SKUs críticos
        if dados.skus_alto_giro_sem_estoque:
            analise.append(f"ATENÇÃO: {len(dados.skus_alto_giro_sem_estoque)} SKU(s) de alto giro estão sem estoque, o que pode resultar em perda de vendas. ")
        
        # Análise de reposição
        if dados.itens_a_repor:
            analise.append(f"São necessárias ações de reposição para {len(dados.itens_a_repor)} item(ns) que apresentam estoque abaixo do ideal. ")
        
        # Análise de risco SKU_1
        if "muito alto" in dados.risco_desabastecimento_sku1.lower():
            analise.append(f"CRÍTICO: O SKU_1 apresenta risco muito alto de desabastecimento. Recomenda-se priorizar a reposição imediata.")
        elif "alto" in dados.risco_desabastecimento_sku1.lower():
            analise.append(f"ALERTA: O SKU_1 requer atenção devido ao risco alto de desabastecimento.")
        else:
            analise.append(f"O SKU_1 apresenta situação estável no momento.")
        
        return "".join(analise)

    def gerar_str_boletim(self, dados: DadosBoletimModel) -> str:
        """Gera o boletim corporativo com análise da IA"""
        
        # Primeiro, cria o relatório estruturado
        relatorio_estruturado = self._formatar_dados_estruturados(dados)
        
        # Prompt mais direto e focado
        prompt = f"""Analise os indicadores de supply chain abaixo e escreva 2-3 parágrafos destacando os principais riscos e oportunidades:

Estoque consumido: {dados.qtd_estoque_consumido_ton} toneladas
Aging médio: {dados.valor_aging_avg} semanas
SKUs sem estoque: {len(dados.skus_alto_giro_sem_estoque)}
Risco SKU_1: {dados.risco_desabastecimento_sku1}

Análise:"""

        try:
            # Usando torch.no_grad() para garantir que não haja atualizações de gradientes
            with torch.no_grad():
                input_ids = self.tokenizer(prompt, return_tensors="pt")
                input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

                # Parâmetros determinísticos para resultados consistentes
                outputs = self.model.generate(
                    **input_ids, 
                    max_new_tokens=250,
                    temperature=0,  # temperatura zero para determinismo
                    do_sample=False,  # desativa amostragem aleatória
                    repetition_penalty=1.4,
                    no_repeat_ngram_size=4,
                    pad_token_id=self.tokenizer.eos_token_id,
                    seed=42  # seed fixa para consistência
                )
            output_str = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extrai apenas a parte após "Análise:"
            texto_ia = re.split(r'Análise:\s*', output_str, flags=re.IGNORECASE)
            if len(texto_ia) > 1:
                texto_ia = texto_ia[1].strip()
            else:
                texto_ia = output_str.strip()
            
            # Limpeza agressiva: remove URLs, prompts repetidos e lixo
            texto_ia = re.sub(r'https?://[^\s]+', '', texto_ia)  # Remove URLs
            texto_ia = re.sub(r'www\.[^\s]+', '', texto_ia)  # Remove www links
            texto_ia = re.sub(r'docs\.google\.[^\s]+', '', texto_ia)  # Remove Google Docs links
            texto_ia = re.sub(r'(Analise os|Escreva|Você é).*?(?=\n|$)', '', texto_ia, flags=re.IGNORECASE)
            texto_ia = re.sub(r'<[^>]+>', '', texto_ia)  # Remove tags HTML
            texto_ia = re.sub(r'\s+', ' ', texto_ia)  # Normaliza espaços
            texto_ia = texto_ia.strip()
            
            # Se o texto da IA for muito curto ou inválido, usa análise baseada em regras
            if len(texto_ia) < 50 or 'http' in texto_ia.lower() or 'google' in texto_ia.lower():
                print("⚠️ IA gerou output inválido, usando análise baseada em regras")
                texto_ia = self._gerar_analise_baseada_regras(dados)
            
            # Combina dados estruturados + análise
            boletim_final = f"""{relatorio_estruturado}

📝 ANÁLISE E RECOMENDAÇÕES

{texto_ia}
"""
            
            return boletim_final
            
        except Exception as e:
            print(f"Erro ao gerar texto com IA: {e}")
            # Fallback: usa análise baseada em regras
            analise = self._gerar_analise_baseada_regras(dados)
            return f"""{relatorio_estruturado}

📝 ANÁLISE E RECOMENDAÇÕES

{analise}
"""