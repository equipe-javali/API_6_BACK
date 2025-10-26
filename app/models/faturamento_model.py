import datetime


class FaturamentoModel:
    def __init__(self,
            data: datetime,
            cod_cliente: int,
            lote: str,
            origem: str,
            zs_gr_mercad: str,
            produto: str,
            cod_produto: str,
            zs_centro: str,
            zs_cidade: str,
            zs_uf: str,
            zs_peso_liquido: float,
            giro_sku_cliente: float,
            SKU: str
        ):
        self.data = data
        self.cod_cliente = cod_cliente
        self.lote = lote
        self.origem = origem
        self.zs_gr_mercad = zs_gr_mercad
        self.produto = produto
        self.cod_produto = cod_produto
        self.zs_centro = zs_centro
        self.zs_cidade = zs_cidade
        self.zs_uf = zs_uf
        self.zs_peso_liquido = zs_peso_liquido
        self.giro_sku_cliente = giro_sku_cliente
        self.SKU = SKU
