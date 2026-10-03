from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AlimentacionCreate(BaseModel):
    lote_id: int
    producto_id: int
    fecha_hora: datetime
    cantidad: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3)
    observaciones: Optional[str] = None


class AlimentacionOut(BaseModel):
    id: int
    lote_id: int
    producto_id: int
    fecha_hora: datetime
    cantidad: Decimal
    observaciones: Optional[str] = None
    registrado_por: int
    created_at: datetime

    class Config:
        from_attributes = True


class AlimentacionConStockOut(AlimentacionOut):
    stock_restante: Optional[Decimal] = None
