import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()
HG_TOKEN = os.getenv("HG_TOKEN")

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
        
        prompt = f"""Você é um assistente de análise de dados empresariais.
        
        PERGUNTA: {pergunta}
        
        Responda de forma clara, objetiva e profissional em português.
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