import pandas
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.enviar_email import enviar_email
from models.relatorio_model import get_usuarios_boletim
from services.boletim_service import BoletimService
from models.dados_boletim_model import DadosBoletimModel
from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel
from models.envio_semanal_model import _ler_periodo_banco
from models.envio_semanal_model import _salvar_periodo_banco

router = APIRouter()


def _gerar_periodo_boletim() -> tuple[str, str]:
    """Gera período do boletim a partir do banco"""
    data_inicio, data_fim = _ler_periodo_banco()
    
    if not data_inicio or not data_fim:
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(weeks=52)
    
    return data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y")



def _gerar_html_email(boletim_texto: str, data_inicio: datetime, data_fim: datetime) -> str:
    """Gera o HTML formatado para email"""
    
    assunto = f"Boletim Corporativo {data_inicio} a {data_fim}"
    print(data_inicio, data_fim)
    
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

# -------------------
# ENVIO SEMANAL
# -------------------

def verificar_envio_semanal():
    """Verifica se já passou 1 semana desde o último boletim"""
    data_inicio_antiga, data_fim_antiga = _ler_periodo_banco()

    if not data_fim_antiga:
        print("Nenhum envio anterior encontrado. Gerando primeiro boletim...")
        hoje = datetime.now()
        _salvar_periodo_banco(hoje - timedelta(days=7), hoje)
        enviar_relatorio()
        return

    dias_desde_ultimo = (datetime.now().date() - data_fim_antiga.date()).days
    print(f"Último boletim enviado há {dias_desde_ultimo} dia(s).")

    if dias_desde_ultimo >= 7:
        print("Já se passou uma semana. Gerando novo boletim...")
        hoje = datetime.now()
        _salvar_periodo_banco(data_fim_antiga + timedelta(days=1), hoje)
        enviar_relatorio()
    else:
        print("Ainda não passou uma semana. Nenhum boletim enviado.")



@router.post("/enviar-relatorio")
def enviar_relatorio():
    """Gera e envia o boletim corporativo por email"""
    try:
        print("Iniciando processo de envio de boletim...")
        
        # 1. Buscar usuários que recebem boletim
        usuarios = get_usuarios_boletim()
        destinatarios = [u["email"] for u in usuarios]

        if not destinatarios:
            raise HTTPException(status_code=404, detail="Nenhum usuário para boletim encontrado.")
        
        print(f"✅ {len(destinatarios)} destinatário(s) encontrado(s): {destinatarios}")

        # 2. Carregar dados dos CSVs
        print("Carregando dados dos CSVs...")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        estoque_path = os.path.join(base_dir, "db", "estoque 1.csv")
        faturamento_path = os.path.join(base_dir, "db", "faturamento 1.csv")
        
        estoque_df = pandas.read_csv(estoque_path, encoding="utf-8", sep="|")
        faturamento_df = pandas.read_csv(faturamento_path, encoding="utf-8", sep="|")
        
        print(f"✅ {len(estoque_df)} registros de estoque carregados")
        print(f"✅ {len(faturamento_df)} registros de faturamento carregados")

        # 3. Converter para modelos
        dados_estoque = [EstoqueModel(*values) for values in estoque_df.values]
        dados_faturamento = [FaturamentoModel(*values) for values in faturamento_df.values]

        # 4. Processar dados e gerar indicadores
        print("Processando indicadores...")
        dados_boletim = DadosBoletimModel.from_raw_data(dados_estoque, dados_faturamento)
        print(f"Indicadores gerados: {dados_boletim.qtd_estoque_consumido_ton}t consumidas")

        # 5. Gerar boletim com IA
        print("🤖 Gerando boletim com IA...")
        boletim_service = BoletimService()
        boletim_texto = boletim_service.gerar_str_boletim(dados_boletim)
        print(f"✅ Boletim gerado ({len(boletim_texto)} caracteres)")

        # 6. Criar HTML formatado
        conteudo_html = _gerar_html_email(boletim_texto, data_inicio, data_fim)
        
        # 7. Gerar assunto com período
        data_inicio, data_fim = _gerar_periodo_boletim()
        assunto = f"Boletim Corporativo {data_inicio} a {data_fim}"

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
