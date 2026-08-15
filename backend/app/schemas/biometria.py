from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class BiometriaCreate(BaseModel):
    lote_id: int
    fecha_hora: datetime
    cantidad_muestra: int
    peso_total_muestra: float
    observaciones: Optional[str] = None
    talla_promedio: Optional[float] = None
    unidad_talla: Optional[str] = None

    @field_validator("cantidad_muestra")
    @classmethod
    def cantidad_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cantidad_muestra debe ser mayor que 0")
        return v

    @field_validator("peso_total_muestra")
    @classmethod
    def peso_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("peso_total_muestra debe ser mayor que 0")
        return v

    @field_validator("talla_promedio")
    @classmethod
    def talla_no_negativa(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("talla_promedio debe ser >= 0")
        return v


class BiometriaOut(BaseModel):
    id: int
    lote_id: int
    fecha_hora: datetime
    cantidad_muestra: int
    peso_total_muestra: float
    observaciones: Optional[str] = None
    registrado_por: int
    talla_promedio: Optional[float] = None
    unidad_talla: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
