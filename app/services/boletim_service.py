prompt = """
Escreva um boletim corporativo em português, em parágrafos corridos, usando linguagem formal e profissional. Escreva texto contínuo dividido em parágrafos. Use apenas os dados fornecidos para compor o relatório. Seja mais analítico do que descritivo: conecte as métricas entre si, aponte implicações operacionais e conclua com uma avaliação de risco prática e objetiva sem recomendações. O boletim deve conter de 400 a 1000 palavras.

Pontos obrigatórios a contemplar no texto (sem numerar na saída): A quantidade total de estoque consumido em toneladas nas últimas 52 semanas foi de 35.000; A frequência de compra (meses com zs_peso_liquido > 0) nas últimas 52 semanas foi de 7; O valor do aging de estoque (em semanas) foi de 3; O número de clientes que consomem o SKU_1 é 10; Os SKUs 13, 20 e 28 foram identificados como de alto giro e alta frequência e estão sem estoque; Os itens SKU 5, 10, 13, 20, 25 e 28 que precisam ser repostos; O risco de desabastecimento do SKU_1 é baixo. Integre essas informações em um fluxo narrativo lógico e coeso.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

import time

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-2b-it")
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2-2b-it",
    device_map="auto",
    dtype=torch.bfloat16,
)

start_time = time.perf_counter()

input_text = prompt
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

outputs = model.generate(**input_ids, max_new_tokens=1024)

end_time = time.perf_counter()
execution_time = end_time - start_time
print(f"Execution time: {execution_time:.4f} seconds")

with open("output.md", "w", encoding="utf-8") as file:
    file.write(tokenizer.decode(outputs[0]))
