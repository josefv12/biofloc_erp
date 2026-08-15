from decimal import Decimal
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class DetalleVentaBase(BaseModel):
    lote_id: int
    cantidad: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    precio_unitario: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)


class DetalleVentaCreate(DetalleVentaBase):
    pass


class DetalleVentaOut(DetalleVentaBase):
    id: int
    venta_id: int
    subtotal: Decimal = Field(..., max_digits=14, decimal_places=2)
    model_config = ConfigDict(from_attributes=True)


class VentaBase(BaseModel):
    fecha: date
    cliente: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None


class VentaCreate(VentaBase):
    detalles: List[DetalleVentaCreate]


class VentaOut(VentaBase):
    id: int
    total: Decimal = Field(..., max_digits=14, decimal_places=2)
    registrado_por: int
    created_at: object
    detalles: List[DetalleVentaOut]
    model_config = ConfigDict(from_attributes=True)
