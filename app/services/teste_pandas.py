import pandas

from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel
from models.dados_boletim_model import DadosBoletimModel
from services.boletim_service import BoletimService

estoque_df = pandas.read_csv("estoque 1.csv", encoding="utf-8", sep="|")
faturamento_df = pandas.read_csv("faturamento 1.csv", encoding="utf-8", sep="|")

dados_estoque = [EstoqueModel(*values) for values in estoque_df.values]
dados_faturamento = [FaturamentoModel(*values) for values in faturamento_df.values]

dados_boletim = DadosBoletimModel.from_raw_data(dados_estoque, dados_faturamento)
boletim_str = BoletimService().gerar_str_boletim(dados_boletim)
with open("teste.md", "w", encoding="utf-8") as file: file.write(boletim_str)