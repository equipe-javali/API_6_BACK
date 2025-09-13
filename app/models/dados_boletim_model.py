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
