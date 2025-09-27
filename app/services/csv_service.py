import csv
import io
from datetime import datetime
from typing import List, Dict, Any
from db.neon_db import NeonDB
from models.csv_models import FaturamentoCsvModel, EstoqueCsvModel

class CsvService:
    def __init__(self):
        pass

    def processar_csv_faturamento(self, csv_content: str) -> Dict[str, Any]:
        """Processa CSV de faturamento e salva no banco de dados."""
        try:
            registros_processados = 0
            registros_com_erro = 0
            erros = []

            csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter='|')
            
            with NeonDB() as db:
                for linha_num, linha in enumerate(csv_reader, start=2):
                    try:
                        faturamento = FaturamentoCsvModel(
                            data=datetime.strptime(linha['data'], '%Y-%m-%d').date(),
                            cod_cliente=int(linha['cod_cliente']),
                            lote=linha['lote'].strip(),
                            origem=linha['origem'].strip(),
                            zs_gr_mercad=linha['zs_gr_mercad'].strip(),
                            produto=linha['produto'].strip(),
                            cod_produto=linha['cod_produto'].strip(),
                            zs_centro=linha['zs_centro'].strip(),
                            zs_cidade=linha['zs_cidade'].strip(),
                            zs_uf=linha['zs_uf'].strip(),
                            zs_peso_liquido=float(linha['zs_peso_liquido']),
                            giro_sku_cliente=float(linha['giro_sku_cliente']),
                            SKU=linha['SKU'].strip()
                        )

                        query = """
                        INSERT INTO faturamento 
                        (data, cod_cliente, lote, origem, zs_gr_mercad, produto, cod_produto, 
                         zs_centro, zs_cidade, zs_uf, zs_peso_liquido, giro_sku_cliente, SKU)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        db.execute(query, [
                            faturamento.data,
                            faturamento.cod_cliente,
                            faturamento.lote,
                            faturamento.origem,
                            faturamento.zs_gr_mercad,
                            faturamento.produto,
                            faturamento.cod_produto,
                            faturamento.zs_centro,
                            faturamento.zs_cidade,
                            faturamento.zs_uf,
                            faturamento.zs_peso_liquido,
                            faturamento.giro_sku_cliente,
                            faturamento.SKU
                        ])
                        
                        registros_processados += 1

                    except Exception as e:
                        registros_com_erro += 1
                        erros.append(f"Linha {linha_num}: {str(e)}")
                        continue

                db.commit()

            return {
                "success": True,
                "message": "CSV de faturamento processado com sucesso",
                "detalhes": {
                    "registros_processados": registros_processados,
                    "registros_com_erro": registros_com_erro,
                    "erros": erros[:10]
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Erro ao processar CSV de faturamento: {str(e)}",
                "detalhes": {
                    "registros_processados": 0,
                    "registros_com_erro": 0,
                    "erros": [str(e)]
                }
            }

    def processar_csv_estoque(self, csv_content: str) -> Dict[str, Any]:
        """Processa CSV de estoque e salva no banco de dados."""
        try:
            registros_processados = 0
            registros_com_erro = 0
            erros = []

            csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter='|')
            
            with NeonDB() as db:
                for linha_num, linha in enumerate(csv_reader, start=2):
                    try:
                        estoque = EstoqueCsvModel(
                            data=datetime.strptime(linha['data'], '%Y-%m-%d').date(),
                            cod_cliente=int(linha['cod_cliente']),
                            es_centro=linha['es_centro'].strip(),
                            tipo_material=linha['tipo_material'].strip(),
                            origem=linha['origem'].strip(),
                            cod_produto=linha['cod_produto'].strip(),
                            lote=linha['lote'].strip(),
                            dias_em_estoque=int(linha['dias_em_estoque']),
                            produto=linha['produto'].strip(),
                            grupo_mercadoria=linha['grupo_mercadoria'].strip(),
                            es_totalestoque=float(linha['es_totalestoque']),
                            SKU=linha['SKU'].strip()
                        )

                        query = """
                        INSERT INTO estoque 
                        (data, cod_cliente, es_centro, tipo_material, origem, cod_produto, 
                         lote, dias_em_estoque, produto, grupo_mercadoria, es_totalestoque, SKU)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        db.execute(query, [
                            estoque.data,
                            estoque.cod_cliente,
                            estoque.es_centro,
                            estoque.tipo_material,
                            estoque.origem,
                            estoque.cod_produto,
                            estoque.lote,
                            estoque.dias_em_estoque,
                            estoque.produto,
                            estoque.grupo_mercadoria,
                            estoque.es_totalestoque,
                            estoque.SKU
                        ])
                        
                        registros_processados += 1

                    except Exception as e:
                        registros_com_erro += 1
                        erros.append(f"Linha {linha_num}: {str(e)}")
                        continue

                db.commit()

            return {
                "success": True,
                "message": "CSV de estoque processado com sucesso",
                "detalhes": {
                    "registros_processados": registros_processados,
                    "registros_com_erro": registros_com_erro,
                    "erros": erros[:10]
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Erro ao processar CSV de estoque: {str(e)}",
                "detalhes": {
                    "registros_processados": 0,
                    "registros_com_erro": 0,
                    "erros": [str(e)]
                }
            }

