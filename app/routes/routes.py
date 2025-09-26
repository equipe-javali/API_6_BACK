import pandas

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.UsuarioService import UsuarioService

from ..services.enviar_email import enviar_email
from ..models.relatorio_model import get_usuarios_boletim
from ..services.boletim_service import BoletimService
from ..models.dados_boletim_model import DadosBoletimModel
from ..models.estoque_model import EstoqueModel
from ..models.faturamento_model import FaturamentoModel

router = APIRouter()
usuario_service = UsuarioService()

class AlterarStatusBoletimRequest(BaseModel):
    user_id: int
    recebe_boletim: bool
    admin_user_id: int

class CriarUsuarioRequest(BaseModel):
    email: str
    senha: str
    recebe_boletim: bool = True

@router.put("/usuario/status-boletim")
def alterar_status_boletim(request: AlterarStatusBoletimRequest):
    """
    Altera o status de recebimento de boletim de um usuário.
    Apenas administradores podem usar esta rota.
    """
    return usuario_service.alterar_status_boletim(
        request.user_id, 
        request.recebe_boletim, 
        request.admin_user_id
    )

@router.get("/usuario/{user_id}/status-boletim")
def get_status_boletim(user_id: int):
    """
    Consulta o status atual de recebimento de boletim de um usuário.
    """
    return usuario_service.get_status_boletim(user_id)

@router.post("/usuario")
def criar_usuario(request: CriarUsuarioRequest):
    try:
        return usuario_service.criar_usuario(
            request.email,
            request.senha,
            request.recebe_boletim
        )
    except Exception as e:
        print(f"[Rota /usuario] Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar usuário")

@router.get("/usuarios")
def listar_usuarios():
    """
    Lista todos os usuários cadastrados.
    """
    return usuario_service.listar_usuarios()

@router.post("/enviar-relatorio")
def enviar_relatorio():
    boletim_service = BoletimService()
    usuarios = get_usuarios_boletim()
    destinatarios = [u["email"] for u in usuarios]

    if not destinatarios:
        raise HTTPException(status_code=404, detail="Nenhum usuário para boletim encontrado.")

    assunto = "Relatório Semanal"
    estoque_df = pandas.read_csv("../db/estoque 1.csv", encoding="utf-8", sep="|")
    faturamento_df = pandas.read_csv("../db/faturamento 1.csv", encoding="utf-8", sep="|")

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
