from pydantic import BaseModel, field_validator
from datetime import date
from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel

class EstoqueCsvModel(BaseModel):
    """Modelo Pydantic para validação de dados CSV de estoque"""
    data: date
    cod_cliente: int
    es_centro: str
    tipo_material: str
    origem: str
    cod_produto: str
    lote: str
    dias_em_estoque: int
    produto: str
    grupo_mercadoria: str
    es_totalestoque: float
    SKU: str

    @field_validator('dias_em_estoque')
    @classmethod
    def validate_dias_estoque(cls, v):
        if v < 0:
            raise ValueError('Dias em estoque não pode ser negativo')
        return v

    @field_validator('es_totalestoque')
    @classmethod
    def validate_estoque(cls, v):
        if v < 0:
            raise ValueError('Estoque total não pode ser negativo')
        return v

    def to_estoque_model(self) -> EstoqueModel:
        """Converte para o modelo original"""
        return EstoqueModel(
            data=self.data.strftime('%Y-%m-%d'),
            cod_cliente=self.cod_cliente,
            es_centro=self.es_centro,
            tipo_material=self.tipo_material,
            origem=self.origem,
            cod_produto=self.cod_produto,
            lote=self.lote,
            dias_em_estoque=self.dias_em_estoque,
            produto=self.produto,
            grupo_mercadoria=self.grupo_mercadoria,
            es_totalestoque=self.es_totalestoque,
            SKU=self.SKU
        )

class FaturamentoCsvModel(BaseModel):
    """Modelo Pydantic para validação de dados CSV de faturamento"""
    data: date
    cod_cliente: int
    lote: str
    origem: str
    zs_gr_mercad: str
    produto: str
    cod_produto: str
    zs_centro: str
    zs_cidade: str
    zs_uf: str
    zs_peso_liquido: float
    giro_sku_cliente: float
    SKU: str

    @field_validator('zs_peso_liquido', 'giro_sku_cliente')
    @classmethod
    def validate_positive_numbers(cls, v):
        if v < 0:
            raise ValueError('Valores devem ser positivos')
        return v

    @field_validator('zs_uf')
    @classmethod
    def validate_uf(cls, v):
        if len(v) != 2:
            raise ValueError('UF deve ter exatamente 2 caracteres')
        return v.upper()

    def to_faturamento_model(self) -> FaturamentoModel:
        """Converte para o modelo original"""
        return FaturamentoModel(
            data=self.data.strftime('%Y-%m-%d'),
            cod_cliente=self.cod_cliente,
            lote=self.lote,
            origem=self.origem,
            zs_gr_mercad=self.zs_gr_mercad,
            produto=self.produto,
            cod_produto=self.cod_produto,
            zs_centro=self.zs_centro,
            zs_cidade=self.zs_cidade,
            zs_uf=self.zs_uf,
            zs_peso_liquido=self.zs_peso_liquido,
            giro_sku_cliente=self.giro_sku_cliente,
            SKU=self.SKU
        )

class CsvTextRequest(BaseModel):
    csv_content: str

    @field_validator('csv_content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Conteúdo CSV não pode estar vazio')
        return v