from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date, time
from decimal import Decimal


class DetalleCompraIn(BaseModel):
    producto_id: int
    cantidad: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    precio_unitario: Decimal = Field(..., ge=0, max_digits=14, decimal_places=2)


class CompraCreate(BaseModel):
    fecha: date
    proveedor: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None
    detalles: list[DetalleCompraIn]


class CompraUpdate(CompraCreate):
    # Hora local de la entrada de inventario; la fecha original de compra no se modifica.
    hora: Optional[time] = None


class DetalleCompraOut(BaseModel):
    id: int
    compra_id: int
    producto_id: int
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class CompraOut(BaseModel):
    id: int
    fecha: date
    proveedor: Optional[str]
    total: Decimal
    observaciones: Optional[str]
    registrado_por: int
    created_at: datetime

    detalles: list[DetalleCompraOut] = []

    model_config = ConfigDict(from_attributes=True)


class CompraDetalleOut(CompraOut):
    movimientos: list[dict] = []