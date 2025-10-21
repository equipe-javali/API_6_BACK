from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.enviar_email import enviar_email
from models.relatorio_model import get_usuarios_boletim
from services.boletim_service import BoletimService
from services.carregar_dados_db import CarregadorDadosDB

router = APIRouter()


def _gerar_periodo_boletim() -> tuple[str, str]:
    """Gera o período do boletim (semana específica para teste)"""
    # Convertendo as strings em objetos datetime
    data_inicio = datetime.strptime('2024-01-10', '%Y-%m-%d')
    data_fim = datetime.strptime('2024-01-15', '%Y-%m-%d')
    return data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y")


def _gerar_html_email(boletim_texto: str) -> str:
    """Gera o HTML formatado para email"""
    data_inicio, data_fim = _gerar_periodo_boletim()
    assunto = f"Boletim Corporativo {data_inicio} a {data_fim}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{assunto}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header {{
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            h1 {{
                color: #2c3e50;
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            .periodo {{
                color: #7f8c8d;
                font-size: 14px;
                font-style: italic;
            }}
            .conteudo {{
                white-space: pre-wrap;
                color: #34495e;
                font-size: 15px;
            }}
            .secao {{
                margin: 25px 0;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ecf0f1;
                text-align: center;
                color: #95a5a6;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 {assunto}</h1>
                <p class="periodo">Período de análise: {data_inicio} a {data_fim}</p>
            </div>
            <div class="conteudo">
{boletim_texto}
            </div>
            <div class="footer">
                <p>Boletim Corporativo gerado automaticamente | {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@router.post("/enviar-relatorio")
def enviar_relatorio():
    """Gera e envia o boletim corporativo por email"""
    try:
        print("📧 Iniciando processo de envio de boletim...")
        
        # 1. Buscar usuários que recebem boletim
        usuarios = get_usuarios_boletim()
        destinatarios = [u["email"] for u in usuarios]

        if not destinatarios:
            raise HTTPException(status_code=404, detail="Nenhum usuário para boletim encontrado.")
        
        print(f"✅ {len(destinatarios)} destinatário(s) encontrado(s)")

        # Obter o período definido
        data_inicio_obj, data_fim_obj = datetime.strptime('2024-01-10', '%Y-%m-%d'), datetime.strptime('2024-01-15', '%Y-%m-%d')
        data_inicio_str, data_fim_str = '2024-01-10', '2024-01-15'  # Formato YYYY-MM-DD para o banco
        
        print(f"📅 Período de análise: {data_inicio_obj.strftime('%d/%m/%Y')} a {data_fim_obj.strftime('%d/%m/%Y')}")

        # 2. Carregar dados do banco de dados
        print("🔗 Conectando ao banco de dados...")
        carregador = CarregadorDadosDB()
        
        try:
            # 3. Processar dados e gerar indicadores com período específico
            print("📊 Carregando dados e processando indicadores...")
            dados_boletim = carregador.gerar_boletim_model(
                data_inicio=data_inicio_str,
                data_fim=data_fim_str
            )
            print(f"✅ Indicadores gerados: {dados_boletim.qtd_estoque_consumido_ton}t consumidas")
        except Exception as e:
            print(f"❌ Erro ao carregar dados do banco: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao carregar dados: {str(e)}")

        # 5. Gerar boletim com IA
        print("🤖 Gerando boletim com IA...")
        boletim_service = BoletimService()
        boletim_texto = boletim_service.gerar_str_boletim(dados_boletim)
        print(f"✅ Boletim gerado ({len(boletim_texto)} caracteres)")

        # 6. Criar HTML formatado
        conteudo_html = _gerar_html_email(boletim_texto)
        
        # 7. Gerar assunto com período
        data_inicio_fmt, data_fim_fmt = data_inicio_obj.strftime("%d/%m/%Y"), data_fim_obj.strftime("%d/%m/%Y")
        assunto = f"Boletim semanal {data_inicio_fmt} a {data_fim_fmt}"

        # 8. Enviar email
        print(f"📤 Enviando email para {len(destinatarios)} destinatário(s)...")
        resultado = enviar_email(destinatarios, assunto, conteudo_html)      

        if resultado["status"] == "erro":
            raise HTTPException(status_code=500, detail=resultado["mensagem"])

        print("✅ Boletim enviado com sucesso!")
        return {
            "message": f"Boletim enviado para {len(destinatarios)} usuários.",
            "assunto": assunto,
            "destinatarios": destinatarios,
            "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao enviar boletim: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar/enviar boletim: {str(e)}")
