import sys
import os
from dotenv import load_dotenv

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.agent_service import AgentService
from app.services.context_service import ContextService
from app.services.QueryAnalyzer import QueryAnalyzer  # Corrigido aqui

def main():
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Debug do token
    hg_token = os.getenv("HG_TOKEN")
    print(f"--- DEBUG: Carregado HG_TOKEN: {hg_token} ---")
    
    print("=== CHATBOT INTERATIVO - DADOS DE ESTOQUE E FATURAMENTO ===")
    print("Digite suas perguntas sobre estoque e faturamento.")
    print("Digite 'sair', 'exit' ou 'quit' para encerrar.")
    print("=" * 60)
    
    try:
        # 1. Instanciar serviços uma única vez
        print("\n1. Inicializando serviços...")
        print("   (Isso pode demorar alguns segundos...)")
        
        agent_service = AgentService()
        context_service = ContextService()
        query_analyzer = QueryAnalyzer() 
        
        print("   ✅ Serviços inicializados com sucesso!")
        print("   📊 Banco de dados conectado e pronto!")
        print("   🤖 Modelo Gemma carregado!")
        
        # 2. Loop interativo de perguntas
        contador_perguntas = 0
        
        # Testar perguntas factuais automaticamente
        print("\n🤖 TESTANDO PERGUNTAS FACTUAIS AUTOMATICAMENTE:")
        perguntas_teste = testar_perguntas_factuais()
        
        for i, pergunta in enumerate(perguntas_teste, 1):
            print(f"\n--- TESTE {i}/{len(perguntas_teste)} ---")
            print(f"Pergunta: {pergunta}")
            
            try:
                foco = query_analyzer.analyze_query(pergunta)
                if not foco:
                    print("❌ Resposta: Desculpe, eu só respondo perguntas relacionadas ao dataset de estoque e faturamento.")
                    continue
                contexto = context_service.generate_context(foco['focus'])
                resposta = agent_service.process_input(pergunta, contexto)
                print(f"✅ Resposta: {resposta}")
            except Exception as e:
                print(f"❌ Erro: {str(e)}")
        
        print("\n" + "="*60)
        print("🎯 TESTES AUTOMÁTICOS CONCLUÍDOS!")
        print("Agora você pode fazer perguntas manuais:")
        
        while True:
            print("\n" + "-" * 60)
            
            # Solicitar pergunta do usuário
            pergunta = input("\n🤔 Sua pergunta: ").strip()
            
            # Verificar se o usuário quer sair
            if pergunta.lower() in ['sair', 'exit', 'quit', 'q', '']:
                print("\n👋 Obrigado por usar o chatbot! Até mais!")
                break
            
            contador_perguntas += 1
            print(f"\n[Pergunta #{contador_perguntas}] Processando: '{pergunta}'")
            
            try:
                # 3. Analisar pergunta
                print("🔍 Analisando pergunta...")
                foco = query_analyzer.analyze_query(pergunta)
                if not foco:
                    print("❌ Resposta: Desculpe, eu só respondo perguntas relacionadas ao dataset de estoque e faturamento.")
                    continue
                # Corrigido aqui - use analyze_query
                print(f"   📋 Foco detectado: {foco}")
                
                # 4. Gerar contexto
                print("📚 Gerando contexto...")
                contexto = context_service.generate_context(foco['focus'])  # Corrigido - use foco['focus']
                print("   ✅ Contexto preparado")
                
                # 5. Processar com AgentService
                print("🤖 Consultando banco de dados e gerando resposta...")
                print("   (Aguarde, o modelo está processando...)")
                
                resposta = agent_service.process_input(pergunta, contexto)
                
                # 6. Exibir resultado
                print("\n" + "=" * 60)
                print("📋 RESPOSTA:")
                print("=" * 60)
                print(f"📊 {resposta}")
                print("=" * 60)
                
            except Exception as e:
                print(f"\n❌ Erro ao processar pergunta: {str(e)}")
                print("💡 Tente reformular sua pergunta ou verifique se ela é sobre estoque/faturamento.")
                continue
        
        print(f"\n📈 Sessão encerrada. Total de perguntas processadas: {contador_perguntas}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário (Ctrl+C)")
        print("👋 Até mais!")
        
    except Exception as e:
        print(f"\n❌ Erro crítico durante a inicialização: {str(e)}")
        print("🔧 Verifique as configurações do banco de dados e modelo.")
        import traceback
        traceback.print_exc()

def testar_perguntas_factuais():
    """Testa várias perguntas factuais para verificar funcionamento"""
    perguntas_teste =  [
        "Quantos registros tem a tabela 'estoque'?",
        "Quantos registros tem a tabela 'faturamento'?",
        "Qual é a data dos registros mais antigos na tabela 'faturamento'?",
        "Qual produto tem maior es_totalestoque na tabela 'estoque'?",
        "Informe o nome de todos os produtos existentes na tabela 'faturamento'.",
        "Quais os diferentes SKUs na tabela 'estoque'?",
        "Que dia é hoje?",
        "Qual a sua idade?"
        "O que posso comer hoje?"
    ]
    
    return perguntas_teste

if __name__ == "__main__":
    main()