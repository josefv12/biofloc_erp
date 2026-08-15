from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class MortalidadCreate(BaseModel):
    lote_id: int
    fecha_hora: datetime
    cantidad: int
    causa: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cantidad debe ser mayor que 0")
        return v


class MortalidadOut(BaseModel):
    id: int
    lote_id: int
    fecha_hora: datetime
    cantidad: int
    causa: Optional[str] = None
    observaciones: Optional[str] = None
    registrado_por: int
    created_at: datetime

    class Config:
        from_attributes = True
