import pandas

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.enviar_email import enviar_email
from ..models.relatorio_model import get_usuarios_boletim
from ..services.boletim_service import BoletimService
from ..models.dados_boletim_model import DadosBoletimModel
from ..models.estoque_model import EstoqueModel
from ..models.faturamento_model import FaturamentoModel

router = APIRouter()

@router.post("/enviar-relatorio")
def enviar_relatorio():
    boletim_service = BoletimService()
    usuarios = get_usuarios_boletim()
    destinatarios = [u["email"] for u in usuarios]

    if not destinatarios:
        raise HTTPException(status_code=404, detail="Nenhum usuário para boletim encontrado.")

    assunto = "Relatório Semanal"
    estoque_df = pandas.read_csv("app/db/estoque 1.csv", encoding="utf-8", sep="|")
    faturamento_df = pandas.read_csv("app/db/faturamento 1.csv", encoding="utf-8", sep="|")

    dados_estoque = [EstoqueModel(*values) for values in estoque_df.values]
    dados_faturamento = [FaturamentoModel(*values) for values in faturamento_df.values]

    dados_boletim = DadosBoletimModel.from_raw_data(dados_estoque, dados_faturamento)
    boletim_texto = boletim_service.gerar_str_boletim(dados_boletim)

    conteudo_html = f"""
    <h1>Relatório Semanal</h1>
    <p>{boletim_texto}</p>
    """

    resultado = enviar_email(destinatarios, assunto, conteudo_html)

    if resultado["status"] == "erro":
        raise HTTPException(status_code=500, detail=resultado["mensagem"])

    return {"message": f"Boletim enviado para {len(destinatarios)} usuários."}
