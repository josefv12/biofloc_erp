from decimal import Decimal
from pydantic import BaseModel, Field


class CostosLoteOut(BaseModel):
    lote_id: int
    codigo: str
    estanque_id: int
    alevinos: Decimal = Field(..., max_digits=18, decimal_places=2)
    alimento: Decimal = Field(..., max_digits=18, decimal_places=2)
    otros_costos_directos: Decimal = Field(..., max_digits=18, decimal_places=2)
    costo_directo_lote: Decimal = Field(..., max_digits=18, decimal_places=2)
    costos_estanque_no_asignados: Decimal = Field(..., max_digits=18, decimal_places=2)
    kg_alimento_suministrado: Decimal = Field(..., max_digits=18, decimal_places=3)
    kg_cosechados: Decimal = Field(..., max_digits=18, decimal_places=3)
    costo_por_kg: Decimal | None = Field(None, max_digits=18, decimal_places=2)
    ventas: Decimal = Field(..., max_digits=18, decimal_places=2)
    kg_vendidos: Decimal = Field(..., max_digits=18, decimal_places=3)
    costo_ventas_estimado: Decimal = Field(..., max_digits=18, decimal_places=2)
    utilidad_bruta_estimada: Decimal | None = Field(None, max_digits=18, decimal_places=2)
    margen_bruto_estimado_pct: Decimal | None = Field(None, max_digits=8, decimal_places=2)
