from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel



class DadosBoletimModel:pass
class DadosBoletimModel:
    def __init__(self,
            qtd_estoque_consumido_ton: int,
            freq_compra: int,
            valor_aging: int,
            qtd_consomem_sku1: int,
            skus_alto_giro_sem_estoque: list[int],
            itens_a_repor: list[str],
            risco_desabastecimento_sku1: float
        ):
        self.qtd_estoque_consumido_ton = qtd_estoque_consumido_ton
        self.freq_compra = freq_compra
        self.valor_aging = valor_aging
        self.qtd_consomem_sku1 = qtd_consomem_sku1
        self.skus_alto_giro_sem_estoque = skus_alto_giro_sem_estoque
        self.itens_a_repor = itens_a_repor
        self.risco_desabastecimento_sku1 = risco_desabastecimento_sku1
    
    def from_raw_data(dados_estoque: list[EstoqueModel], dados_faturamento: list[FaturamentoModel]) -> DadosBoletimModel:
        #TODO
        # Qual a quantidade de estoque consumido em toneladas (es_totalestoque) das últimas 52 semanas?
        # somar os valores da coluna es_totalestoque de dados_estoque

        # Qual a frequência de compra (meses com zs_peso_liquido >0) das últimas 52 semanas?
        # contar quantos dos meses nas últimas 52 semanas possuíram o zs_peso_liquido total > 0

        # O valor do aging de estoque (idade em semanas)?
        # valor médio da coluna dias_em_estoque de dados_estoque

        # Quantos clientes consomem o material SKU_1
        # contar quantos clientes distintos (cod_cliente em dados_estoque) consomem SKU_1

        # Quais SKUs de alto giro e alta frequencia que estão sem estoque?
        # definir o que é um SKU de alto giro e frequencia (coluna giro_sku_cliente em dados_faturamento)

        # Quais são os itens a serem repostos no estoque?
        # <SKUs com alto giro e giro_sku_cliente baixo es_totalestoque???>

        # Qual o risco de desabastecimento do SKU_1?
        # <talvez calcular a quantidade recente está abaixo da média???>

        DadosBoletimModel(
            qtd_estoque_consumido_ton = ,
            freq_compra = ,
            valor_aging = ,
            qtd_consomem_sku1 = ,
            skus_alto_giro_sem_estoque = ,
            itens_a_repor = ,
            risco_desabastecimento_sku1 = 
        )
