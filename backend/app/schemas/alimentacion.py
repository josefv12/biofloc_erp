from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class AlimentacionCreate(BaseModel):
    lote_id: int
    producto_id: int
    fecha_hora: datetime
    cantidad: float
    observaciones: Optional[str] = None

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("cantidad debe ser mayor que 0")
        return v


class AlimentacionOut(BaseModel):
    id: int
    lote_id: int
    producto_id: int
    fecha_hora: datetime
    cantidad: float
    observaciones: Optional[str] = None
    registrado_por: int
    created_at: datetime

    class Config:
        from_attributes = True


class AlimentacionConStockOut(AlimentacionOut):
    stock_restante: Optional[float] = None
