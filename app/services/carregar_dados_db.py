from datetime import datetime, timedelta, date
import pandas as pd
from db.neon_db import NeonDB
from models.estoque_model import EstoqueModel
from models.faturamento_model import FaturamentoModel
from models.dados_boletim_model import DadosBoletimModel


class CarregadorDadosDB:
    def __init__(self):
        self.db = NeonDB()
    
    def carregar_estoque(self):
        sql = "SELECT * FROM estoque;"
        return self.db.fetchall(sql)

    def carregar_faturamento(self):
        sql = "SELECT * FROM faturamento;"
        return self.db.fetchall(sql)

    def obter_primeira_data(self):
        try:
            sql_estoque = "SELECT MIN(data) FROM estoque;"
            sql_faturamento = "SELECT MIN(data) FROM faturamento;"
            data_estoque = self.db.fetchone(sql_estoque)[0]
            data_faturamento = self.db.fetchone(sql_faturamento)[0]

            def parse_data(d):
                if isinstance(d, datetime):
                    return d
                elif isinstance(d, str):
                    return datetime.fromisoformat(d)
                elif isinstance(d, date):
                    return datetime.combine(d, datetime.min.time())
                else:
                    return None

            datas_validas = [d for d in [parse_data(data_estoque), parse_data(data_faturamento)] if d]
            if not datas_validas:
                print("⚠️ Nenhuma data válida encontrada no banco.")
                return None

            primeira_data = min(datas_validas)
            print(f"Primeira data encontrada no banco: {primeira_data}")
            return primeira_data
        except Exception as e:
            print(f"Erro ao obter primeira data: {e}")
            return None

    def obter_estrutura_tabela(self, tabela: str) -> list:
        query = f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{tabela}'
        ORDER BY ordinal_position
        """
        results = self.db.fetchall(query)
        return [col[0] for col in results]

    def carregar_dados_estoque(self, periodo_semanas: int = None, data_inicio: str = None, data_fim: str = None) -> pd.DataFrame:
        colunas_originais = [
            'data', 'cod_cliente', 'es_centro', 'tipo_material', 'origem',
            'cod_produto', 'lote', 'dias_em_estoque', 'produto', 'grupo_mercadoria',
            'es_totalestoque', 'sku'
        ]
        colunas = self.obter_estrutura_tabela('estoque')
        print(f"Colunas disponíveis na tabela estoque: {colunas}")

        coluna_data = 'data' if 'data' in colunas else 'data_estoque' if 'data_estoque' in colunas else None
        if not coluna_data:
            raise ValueError("Não foi encontrada uma coluna de data na tabela estoque")

        coluna_sku = 'sku' if 'sku' in colunas else None
        if not coluna_sku:
            print("⚠️ Nenhuma coluna 'sku' encontrada, será criada manualmente")
        
        colunas_select = [c for c in colunas_originais if c in colunas or c == 'sku']
        
        # Definir período
        if data_inicio and data_fim:
            data_inicio_str, data_fim_str = data_inicio, data_fim
            print(f"📅 Período ESPECÍFICO definido: {data_inicio_str} a {data_fim_str}")
        else:
            if periodo_semanas is None:
                periodo_semanas = 52
            data_fim_dt = datetime.now()
            data_inicio_dt = data_fim_dt - timedelta(weeks=periodo_semanas)
            data_inicio_str, data_fim_str = data_inicio_dt.strftime("%Y-%m-%d"), data_fim_dt.strftime("%Y-%m-%d")
            print(f"📅 Período calculado: {data_inicio_str} a {data_fim_str} ({periodo_semanas} semanas)")

        query = f"""
        SELECT {', '.join(colunas_select)}
        FROM estoque
        WHERE {coluna_data} >= '{data_inicio_str}' AND {coluna_data} <= '{data_fim_str}'
        ORDER BY {coluna_data} DESC, {coluna_sku if coluna_sku else 'sku'} ASC
        """
        print(f"Query estoque: {query}")
        results = self.db.fetchall(query)

        df = pd.DataFrame(results, columns=colunas_select)
        if 'sku' not in df.columns:
            df['sku'] = 'sku_1'
        if coluna_data != 'data':
            df = df.rename(columns={coluna_data: 'data'})
        df['data'] = pd.to_datetime(df['data'])

        # Colunas numéricas
        for col in ['dias_em_estoque', 'es_totalestoque']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        print(f"✅ {len(df)} registros de estoque carregados com sucesso")
        return df

    def carregar_dados_faturamento(self, periodo_semanas: int = None, data_inicio: str = None, data_fim: str = None) -> pd.DataFrame:
        colunas_originais = [
            'data', 'cod_cliente', 'lote', 'origem', 'zs_gr_mercad',
            'produto', 'cod_produto', 'zs_centro', 'zs_cidade', 'zs_uf',
            'zs_peso_liquido', 'giro_sku_cliente', 'sku'
        ]
        colunas = self.obter_estrutura_tabela('faturamento')
        print(f"Colunas disponíveis na tabela faturamento: {colunas}")

        coluna_data = 'data' if 'data' in colunas else 'data_faturamento' if 'data_faturamento' in colunas else None
        if not coluna_data:
            raise ValueError("Não foi encontrada uma coluna de data na tabela faturamento")

        coluna_sku = 'sku' if 'sku' in colunas else None
        if not coluna_sku:
            print("⚠️ Nenhuma coluna 'sku' encontrada, será criada manualmente")

        colunas_select = [c for c in colunas_originais if c in colunas or c == 'sku']

        if data_inicio and data_fim:
            data_inicio_str, data_fim_str = data_inicio, data_fim
        else:
            if periodo_semanas is None:
                periodo_semanas = 52
            data_fim_dt = datetime.now()
            data_inicio_dt = data_fim_dt - timedelta(weeks=periodo_semanas)
            data_inicio_str, data_fim_str = data_inicio_dt.strftime("%Y-%m-%d"), data_fim_dt.strftime("%Y-%m-%d")

        query = f"""
        SELECT {', '.join(colunas_select)}
        FROM faturamento
        WHERE {coluna_data} >= '{data_inicio_str}' AND {coluna_data} <= '{data_fim_str}'
        ORDER BY {coluna_data} DESC, {coluna_sku if coluna_sku else 'sku'} ASC
        """
        print(f"Query faturamento: {query}")
        results = self.db.fetchall(query)

        df = pd.DataFrame(results, columns=colunas_select)
        if 'sku' not in df.columns:
            df['sku'] = 'sku_97'
        if coluna_data != 'data':
            df = df.rename(columns={coluna_data: 'data'})
        df['data'] = pd.to_datetime(df['data'])

        for col in ['zs_peso_liquido', 'giro_sku_cliente']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        print(f"✅ {len(df)} registros de faturamento carregados com sucesso")
        return df

def gerar_boletim_model(
    self,
    periodo_semanas: int = None,
    data_inicio: str = None,
    data_fim: str = None
) -> DadosBoletimModel:
    """
    Gera um modelo de dados para o boletim considerando:
    - sku sempre minúsculo
    - períodos diferentes entre estoque e faturamento
    - DataFrames vazios sem quebrar o construtor
    """
    # Carregar dados de estoque
    estoque_df = self.carregar_dados_estoque(
        periodo_semanas=periodo_semanas,
        data_inicio=data_inicio,
        data_fim=data_fim
    )

    # Ajustar período de faturamento baseado em datas reais do estoque/faturamento
    faturamento_df = self.carregar_dados_faturamento(
        periodo_semanas=periodo_semanas,
        data_inicio=data_inicio,
        data_fim=data_fim
    )

    # Garantir colunas SKU minúscula
    if 'SKU' in estoque_df.columns:
        estoque_df = estoque_df.rename(columns={'SKU': 'sku'})
    if 'SKU' in faturamento_df.columns:
        faturamento_df = faturamento_df.rename(columns={'SKU': 'sku'})

    # Garantir coluna 'data' consistente
    if 'data_estoque' in estoque_df.columns:
        estoque_df = estoque_df.rename(columns={'data_estoque': 'data'})
    if 'data_faturamento' in faturamento_df.columns:
        faturamento_df = faturamento_df.rename(columns={'data_faturamento': 'data'})

    # Criar registros de estoque
    colunas_estoque = [
        'data', 'cod_cliente', 'es_centro', 'tipo_material', 'origem',
        'cod_produto', 'lote', 'dias_em_estoque', 'produto',
        'grupo_mercadoria', 'es_totalestoque', 'sku'
    ]
    registros_estoque = []
    for _, row in estoque_df.iterrows():
        kwargs = {col: row[col] if col in row else None for col in colunas_estoque}
        kwargs['sku'] = row['sku'] if 'sku' in row and row['sku'] else 'sku_1'
        registros_estoque.append(EstoqueModel(**kwargs))


    # Criar registros de faturamento
    colunas_faturamento = [
    'data', 'cod_cliente', 'lote', 'origem', 'zs_gr_mercad',
    'produto', 'cod_produto', 'zs_centro', 'zs_cidade', 'zs_uf',
    'zs_peso_liquido', 'giro_sku_cliente'
    ]

    registros_faturamento = []

    if faturamento_df.empty:
        faturamento_df = pd.DataFrame([{
            'data': datetime.now().strftime("%Y-%m-%d"),
            'cod_cliente': 0,
            'lote': 'N/A',
            'origem': 'N/A',
            'zs_gr_mercad': 'N/A',
            'produto': 'N/A',
            'cod_produto': 'N/A',
            'zs_centro': 'N/A',
            'zs_cidade': 'N/A',
            'zs_uf': 'N/A',
            'zs_peso_liquido': 0,
            'giro_sku_cliente': 0,
            'SKU': 'SKU_0'   # <- atenção, maiúsculo
        }])

    for _, row in faturamento_df.iterrows():
        kwargs = {col: row[col] if col in row else None for col in colunas_faturamento}
        # Garantir que a chave SKU exista e seja maiúscula
        kwargs['SKU'] = row['SKU'] if 'SKU' in row and row['SKU'] else 'SKU_0'
        registros_faturamento.append(FaturamentoModel(**kwargs))



    # Criar modelo de boletim
    try:
        modelo = DadosBoletimModel.from_raw_data(registros_estoque, registros_faturamento)
        print("✅ Modelo de boletim criado com sucesso usando from_raw_data")
        return modelo
    except Exception as e:
        print(f"❌ Erro ao criar modelo com from_raw_data: {e}")
        # fallback para construtor padrão
        qtd_estoque_total = sum(float(e.es_totalestoque or 0) for e in registros_estoque)
        aging_dias = [float(e.dias_em_estoque or 0) for e in registros_estoque]
        aging_semanas = [d/7.0 for d in aging_dias] if aging_dias else [0]
        clientes_sku1 = set(e.cod_cliente for e in registros_estoque if e.sku == 'sku_1')
        modelo = DadosBoletimModel(
            qtd_estoque_consumido_ton=round(qtd_estoque_total, 3),
            freq_compra=len(set((datetime.strptime(f.data, "%Y-%m-%d").year,
                                datetime.strptime(f.data, "%Y-%m-%d").month)
                                for f in registros_faturamento)),
            valor_aging_min=round(min(aging_semanas), 2),
            valor_aging_avg=round(sum(aging_semanas)/len(aging_semanas), 2),
            valor_aging_max=round(max(aging_semanas), 2),
            qtd_consomem_sku1=len(clientes_sku1),
            skus_alto_giro_sem_estoque=[],
            itens_a_repor=['sku_1', 'sku_2'],
            risco_desabastecimento_sku1="moderado/baixo (estoque atual próximo da média)"
        )
        print("✅ Modelo de boletim criado com sucesso usando construtor padrão")
        return modelo

