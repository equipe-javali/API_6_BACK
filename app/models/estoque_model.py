import datetime


class EstoqueModel:
    def __init__(self,
            data: datetime,
            cod_cliente: int,
            es_centro: str,
            tipo_material: str,
            origem: str,
            cod_produto: str,
            lote: str,
            dias_em_estoque: int,
            produto: str,
            grupo_mercadoria: str,
            es_totalestoque: float,
            SKU: str
        ):
        self.data = data
        self.cod_cliente = cod_cliente
        self.es_centro = es_centro
        self.tipo_material = tipo_material
        self.origem = origem
        self.cod_produto = cod_produto
        self.lote = lote
        self.dias_em_estoque = dias_em_estoque
        self.produto = produto
        self.grupo_mercadoria = grupo_mercadoria
        self.es_totalestoque = es_totalestoque
        self.SKU = SKU
