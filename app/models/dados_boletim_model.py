from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel



class DadosBoletimModel:pass
class DadosBoletimModel:
    def __init__(self,
            qtd_estoque_consumido_ton: int,
            freq_compra: int,
            valor_aging_min: int,
            valor_aging_avg: int,
            valor_aging_max: int,
            qtd_consomem_sku1: int,
            skus_alto_giro_sem_estoque: list[int],
            itens_a_repor: list[str],
            risco_desabastecimento_sku1: str
        ):
        self.qtd_estoque_consumido_ton = qtd_estoque_consumido_ton
        self.freq_compra = freq_compra
        self.valor_aging_min = valor_aging_min
        self.valor_aging_avg = valor_aging_avg
        self.valor_aging_max = valor_aging_max
        self.qtd_consomem_sku1 = qtd_consomem_sku1
        self.skus_alto_giro_sem_estoque = skus_alto_giro_sem_estoque
        self.itens_a_repor = itens_a_repor
        self.risco_desabastecimento_sku1 = risco_desabastecimento_sku1
    
    def from_raw_data(dados_estoque: list[EstoqueModel], dados_faturamento: list[FaturamentoModel]) -> DadosBoletimModel:
        #TODO
        # Qual a quantidade de estoque consumido em toneladas (es_totalestoque) das últimas 52 semanas?
        # somar os valores da coluna es_totalestoque de dados_estoque
        qtd_estoque_consumido = sum([dados.es_totalestoque for dados in dados_estoque])

        # Qual a frequência de compra (meses com zs_peso_liquido >0) das últimas 52 semanas?
        # contar quantos dos meses nas últimas 52 semanas possuíram o zs_peso_liquido total > 0

        # O valor do aging de estoque (idade em semanas)?
        # valor médio da coluna dias_em_estoque de dados_estoque

        # Quantos clientes consomem o material SKU_1
        # contar quantos clientes distintos (cod_cliente em dados_estoque) consomem SKU_1
        qtd_consomem_sku1 = len(set([dados.cod_cliente for dados in dados_estoque if dados.SKU == "SKU_1"]))

        # Quais SKUs de alto giro e alta frequencia que estão sem estoque?
        # definir o que é um SKU de alto giro e frequencia (coluna giro_sku_cliente em dados_faturamento)

        # Quais são os itens a serem repostos no estoque?
        # <SKUs com alto giro_sku_cliente e baixo es_totalestoque???>

        # Qual o risco de desabastecimento do SKU_1?
        # <talvez calcular a quantidade recente está abaixo da média???>
        risco_desabastecimento_sku1 = "desconhecido"
        if atual < media:
            risco_desabastecimento_sku1 = "alto, pois o estoque atual está abaixo da média das últimas 52 semanas"
        elif atual == media:
            risco_desabastecimento_sku1 = "baixo, pois o estoque atual está próximo da média das últimas 52 semanas"
        elif atual > media:
            risco_desabastecimento_sku1 = "muito baixo, pois o estoque atual está acima da média das últimas 52 semanas"

        return DadosBoletimModel(
            qtd_estoque_consumido_ton = ,
            freq_compra = ,
            valor_aging = ,
            qtd_consomem_sku1 = ,
            skus_alto_giro_sem_estoque = ,
            itens_a_repor = ,
            risco_desabastecimento_sku1 = 
        )

    def get_report_str(self) -> str:
        return f"A quantidade total de estoque consumido em toneladas nas últimas 52 semanas foi de {self.qtd_estoque_consumido_ton}; A frequência de compra (meses com zs_peso_liquido > 0) nas últimas 52 semanas foi de {self.freq_compra} ou {(52/4) / self.freq_compra}; O valor do aging de estoque (em semanas) mínimo, médio e máximo foram respectivamente {self.valor_aging_min}, {self.valor_aging_avg} e {self.valor_aging_max}; O número de clientes que consomem o SKU_1 é {self.qtd_consomem_sku1}; Os itens com SKU {', '.join(self.skus_alto_giro_sem_estoque)} foram identificados como de alto giro e alta frequência e estão sem estoque; Os itens SKU {', '.join(self.itens_a_repor)} que precisam ser repostos; O risco de desabastecimento do SKU_1 é {self.risco_desabastecimento_sku1}."