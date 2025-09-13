from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

from models.dados_boletim_model import DadosBoletimModel


class BoletimService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("Using device:", self.device)

        if self.device.type == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                "google/gemma-2-2b-it",
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

    def gerar_str_boletim(self, dados: DadosBoletimModel) -> str:
        #TODO
        # Inserir no prompt os valores reais do boletim
        prompt = """
Escreva um boletim corporativo em português, em parágrafos corridos, usando linguagem formal e profissional. Escreva texto contínuo dividido em parágrafos. Use apenas os dados fornecidos para compor o relatório. Seja mais analítico do que descritivo: conecte as métricas entre si, aponte implicações operacionais e conclua com uma avaliação de risco prática e objetiva sem recomendações. O boletim deve conter de 400 a 1000 palavras.

Pontos obrigatórios a contemplar no texto (sem numerar na saída): A quantidade total de estoque consumido em toneladas nas últimas 52 semanas foi de 35.000; A frequência de compra (meses com zs_peso_liquido > 0) nas últimas 52 semanas foi de 7; O valor do aging de estoque (em semanas) foi de 3; O número de clientes que consomem o SKU_1 é 10; Os SKUs 13, 20 e 28 foram identificados como de alto giro e alta frequência e estão sem estoque; Os itens SKU 5, 10, 13, 20, 25 e 28 que precisam ser repostos; O risco de desabastecimento do SKU_1 é baixo. Integre essas informações em um fluxo narrativo lógico e coeso.
"""
        input_ids = self.tokenizer(prompt, return_tensors="pt")
        input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

        outputs = self.model.generate(**input_ids, max_new_tokens=1024)
        #TODO
        # tratar a saida para retirar o que não faz parte da resposta

        return outputs
