from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class MovimientoInventarioBase(BaseModel):
    producto_id: int
    tipo_movimiento_id: int
    cantidad: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    fecha_hora: Optional[datetime] = None
    referencia_tipo: Optional[str] = Field(None, max_length=40)
    referencia_id: Optional[int] = None
    observaciones: Optional[str] = None
    costo_unitario: Optional[Decimal] = Field(None, ge=0, max_digits=14, decimal_places=2)
    costo_total: Optional[Decimal] = Field(None, ge=0, max_digits=16, decimal_places=2)


class MovimientoInventarioCreate(MovimientoInventarioBase):
    pass


class MovimientoInventarioOut(MovimientoInventarioBase):
    id: int
    fecha_hora: datetime
    registrado_por: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
