from datetime import datetime, timedelta
from statistics import mean
import math

from .estoque_model import EstoqueModel
from .faturamento_model import FaturamentoModel



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
    
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d")
    
    @staticmethod
    def _percentile(sorted_vals: list[float], perc: float) -> float:
        """Retorna percentil (perc em 0..100) de lista já ordenada.
           Se lista vazia retorna 0.0."""
        if not sorted_vals:
            return 0.0
        n = len(sorted_vals)
        if n == 1:
            return float(sorted_vals[0])
        
        k = (perc / 100.0) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_vals[int(k)])
        d = k - f
        return float(sorted_vals[f] * (1 - d) + sorted_vals[c] * d)

    @staticmethod
    def from_raw_data(dados_estoque: list[EstoqueModel], dados_faturamento: list[FaturamentoModel]) -> DadosBoletimModel:
        reference_date = datetime.now()
        cutoff = reference_date - timedelta(weeks=52)

        estoque_filtered = []
        faturamento_filtered = []

        # filtrar por últimas 52 semanas
        for e in dados_estoque:
            d = DadosBoletimModel._parse_date(e.data)
            if d is None or d >= cutoff:
                estoque_filtered.append(e)

        for f in dados_faturamento:
            d = DadosBoletimModel._parse_date(f.data)
            if d is None or d >= cutoff:
                faturamento_filtered.append(f)

        # qtd_estoque_consumido_ton
        qtd_estoque_consumido = sum(
            float(e.es_totalestoque or 0) for e in estoque_filtered
        )

        # freq_compra: meses com zs_peso_liquido > 0
        meses_com_compra: set[tuple] = set()
        for f in faturamento_filtered:
            peso = f.zs_peso_liquido or 0
            d = DadosBoletimModel._parse_date(f.data)
            if peso > 0:
                if d:
                    meses_com_compra.add((d.year, d.month))
                else:pass
        freq_compra = len(meses_com_compra)

        # aging (dias_em_estoque -> semanas)
        dias_lista = []
        for e in estoque_filtered:
            val = e.dias_em_estoque
            if val is None:
                continue
            try:
                dias_lista.append(float(val))
            except Exception:
                continue

        if dias_lista:
            semanas = [d / 7.0 for d in dias_lista]
            valor_aging_min = min(semanas)
            valor_aging_avg = mean(semanas)
            valor_aging_max = max(semanas)
        else:
            valor_aging_min = valor_aging_avg = valor_aging_max = 0.0

        # qtd de clientes que consomem SKU_1
        clientes_sku1 = {
            e.cod_cliente
            for e in estoque_filtered
            if e.SKU == "SKU_1"
            and e.cod_cliente is not None
        }
        qtd_consomem_sku1 = len(clientes_sku1)

        # identificar SKUs de alto giro (top quantil)
        # coletar giro por SKU a partir de faturamento (agregando média por SKU)
        from collections import defaultdict

        giro_vals_by_sku = defaultdict(list)
        for f in faturamento_filtered:
            sku = f.SKU
            giro = f.giro_sku_cliente
            if sku is None or giro is None:
                continue
            try:
                giro_vals_by_sku[sku].append(float(giro))
            except Exception:
                continue

        # média de giro por SKU
        giro_media_por_sku = {}
        for sku, vals in giro_vals_by_sku.items():
            if vals:
                giro_media_por_sku[sku] = mean(vals)
        giro_medias_sorted = sorted(giro_media_por_sku.values())

        # high_giro_quantile e giro_cutoff
        # quantil a usar (75º percentil -> top 25%)
        high_giro_quantile = 75.0
        giro_cutoff = DadosBoletimModel._percentile(giro_medias_sorted, high_giro_quantile) if giro_medias_sorted else float("inf")
        skus_alto_giro = {sku for sku, g in giro_media_por_sku.items() if g >= giro_cutoff}

        # estoque atual por SKU (último registro) e estoque agregado
        estoque_por_sku = defaultdict(list)
        for e in estoque_filtered:
            sku = e.SKU
            if sku is None:
                continue
            try:
                estoque_por_sku[sku].append(float(e.es_totalestoque or 0))
            except Exception:
                continue

        # low_stock_threshold baseado nas médias de estoque por SKU
        avg_stock_per_sku = [mean(vals) for vals in estoque_por_sku.values() if vals]
        avg_stock_per_sku_sorted = sorted(avg_stock_per_sku)
        # usamos 25º percentil das médias de estoque como threshold automático
        low_stock_threshold = DadosBoletimModel._percentile(avg_stock_per_sku_sorted, 25.0) if avg_stock_per_sku_sorted else 0.0

        # definir SKUs de alto giro sem estoque (algum registro com es_totalestoque == 0 OU média 0)
        skus_alto_giro_sem_estoque = []
        for sku in skus_alto_giro:
            vals = estoque_por_sku.get(sku, [])
            if not vals or all(v == 0 for v in vals):
                skus_alto_giro_sem_estoque.append(sku)

        # itens a repor: SKUs de alto giro com estoque médio baixo
        itens_a_repor = []
        for sku in skus_alto_giro:
            vals = estoque_por_sku.get(sku, [])
            avg_stock = mean(vals) if vals else 0.0
            if avg_stock < low_stock_threshold:
                itens_a_repor.append(sku)

        # risco de desabastecimento do SKU_1
        sku1_vals = estoque_por_sku.get("SKU_1", [])
        if sku1_vals:
            atual = sku1_vals[-1]
            media = mean(sku1_vals)
            ratio = atual / media if media and media != 0 else float("inf") if atual > 0 else 0.0
            if media == 0 and atual == 0:
                risco = "indefinido (não há histórico de estoque)"
            elif ratio < 0.5:
                risco = "muito alto (estoque atual < 50% da média das últimas 52 semanas)"
            elif ratio < 0.9:
                risco = "alto (estoque atual abaixo da média)"
            elif ratio <= 1.1:
                risco = "moderado/baixo (estoque atual próximo da média)"
            else:
                risco = "muito baixo (estoque atual acima da média)"
        else:
            risco = "indefinido (nenhum registro de SKU_1 nas últimas 52 semanas)"

        return DadosBoletimModel(
            qtd_estoque_consumido_ton=round(qtd_estoque_consumido, 3),
            freq_compra=freq_compra,
            valor_aging_min=round(valor_aging_min, 2),
            valor_aging_avg=round(valor_aging_avg, 2),
            valor_aging_max=round(valor_aging_max, 2),
            qtd_consomem_sku1=qtd_consomem_sku1,
            skus_alto_giro_sem_estoque=sorted(skus_alto_giro_sem_estoque),
            itens_a_repor=sorted(itens_a_repor),
            risco_desabastecimento_sku1=risco,
        )

    def get_report_str(self) -> str:
        skus_alto = ", ".join(map(str, self.skus_alto_giro_sem_estoque)) or "nenhum"
        itens_repor = ", ".join(map(str, self.itens_a_repor)) or "nenhum"
        return (
            f"A quantidade total de estoque consumido em toneladas nas últimas 52 semanas foi de {self.qtd_estoque_consumido_ton} t.\n"
            f"A frequência de compra (meses com zs_peso_liquido > 0) nas últimas 52 semanas foi de {self.freq_compra} meses.\n"
            f"O valor do aging de estoque (em semanas) mínimo, médio e máximo foram respectivamente {self.valor_aging_min}, {self.valor_aging_avg} e {self.valor_aging_max} semanas.\n"
            f"O número de clientes que consomem o SKU_1 é {self.qtd_consomem_sku1}.\n"
            f"Os SKUs de alto giro e alta frequência que estão sem estoque: {skus_alto}.\n"
            f"Os itens que precisam ser repostos: {itens_repor}.\n"
            f"O risco de desabastecimento do SKU_1 é: {self.risco_desabastecimento_sku1}."
        )
