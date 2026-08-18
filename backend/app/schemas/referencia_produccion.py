from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReferenciaProduccionOut(BaseModel):
    id: int
    especie_id: int
    etapa_productiva_id: int
    semana_desde: int
    semana_hasta: int
    peso_esperado_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, max_digits=6, decimal_places=3)
    observaciones: Optional[str] = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
