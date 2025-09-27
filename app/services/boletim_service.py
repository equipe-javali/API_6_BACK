import re
import os

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

from models.dados_boletim_model import DadosBoletimModel

HG_TOKEN = os.getenv("HG_TOKEN")

class BoletimService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("BoletimService using device:", self.device)

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

    def gerar_str_boletim(self, dados: DadosBoletimModel) -> str:
        prompt = f"""Escreva um boletim corporativo em português, em parágrafos corridos, usando linguagem formal e profissional. Escreva texto contínuo dividido em parágrafos. Use apenas os dados fornecidos para compor o relatório. Seja mais analítico do que descritivo: conecte as métricas entre si, aponte implicações operacionais e conclua com uma avaliação de risco prática e objetiva sem recomendações. O boletim deve conter de 400 a 1000 palavras.
        Pontos obrigatórios a contemplar no texto (sem numerar na saída): {dados.get_report_str()} Integre essas informações em um fluxo narrativo lógico e coeso."""

        input_ids = self.tokenizer(prompt, return_tensors="pt")
        input_ids = {k: v.to(self.device) for k, v in input_ids.items()}

        outputs = self.model.generate(**input_ids, max_new_tokens=1024)
        output_str = self.tokenizer.decode(outputs[0])

        texto_limpo = re.sub(r'.*?Integre essas informações em um fluxo narrativo lógico e coeso\.\n\n', '', output_str, flags=re.DOTALL)
        texto_limpo = re.sub(r'[\n\s]*<end_of_turn>', '', texto_limpo)

        return texto_limpo
