from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BiometriaCreate(BaseModel):
    lote_id: int
    fecha_hora: datetime
    cantidad_muestra: int = Field(..., gt=0)
    peso_total_muestra_g: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    observaciones: Optional[str] = None
    talla_promedio: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    unidad_talla: Optional[str] = None


class BiometriaOut(BaseModel):
    id: int
    lote_id: int
    fecha_hora: datetime
    cantidad_muestra: int
    peso_total_muestra_g: Decimal
    observaciones: Optional[str] = None
    registrado_por: int
    talla_promedio: Decimal | None = None
    unidad_talla: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
