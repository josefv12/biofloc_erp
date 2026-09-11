from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


MONEY = Field(..., max_digits=18, decimal_places=2)
KG = Field(..., max_digits=18, decimal_places=3)


class FinanzasLoteOut(BaseModel):
    lote_id: int
    codigo: str
    ventas: Decimal = MONEY
    kg_vendidos: Decimal = KG
    kg_cosechados: Decimal = KG
    costo_alimento: Decimal = MONEY
    gastos_lote: Decimal = MONEY
    costo_produccion: Decimal = MONEY
    costo_por_kg: Decimal = MONEY
    costo_ventas_estimado: Decimal = MONEY
    utilidad_bruta: Decimal = MONEY
    margen_bruto_pct: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)


class DashboardFinanzasOut(BaseModel):
    periodo_desde: Optional[date] = None
    periodo_hasta: Optional[date] = None
    ventas: Decimal = MONEY
    costo_ventas_estimado: Decimal = MONEY
    utilidad_bruta: Decimal = MONEY
    gastos_operativos: Decimal = MONEY
    utilidad_neta: Decimal = MONEY
    margen_bruto_pct: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    margen_neto_pct: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    kg_vendidos: Decimal = KG
    costo_promedio_kg_vendido: Decimal = MONEY
    costo_produccion_lotes: Decimal = MONEY
    lotes_con_ventas: int
    lotes: list[FinanzasLoteOut]
    metodologia: str
