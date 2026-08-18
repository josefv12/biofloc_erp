from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, date
from typing import Optional


# ── Catálogos incrustados en respuestas ──────────────────────────────────────

class EspecieOut(BaseModel):
    id: int
    nombre_comun: str
    nombre_cientifico: Optional[str] = None

    class Config:
        from_attributes = True


class EtapaProductivaOut(BaseModel):
    id: int
    nombre: str
    orden: int

    class Config:
        from_attributes = True


class EstadoLoteOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


# ── Lote ─────────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    codigo: str
    estanque_id: int
    especie_id: int
    etapa_productiva_id: int
    estado_id: int
    fecha_siembra: date
    fecha_cierre: Optional[date] = None
    cantidad_sembrada: int
    peso_inicial_promedio_g: Optional[float] = None
    observaciones: Optional[str] = None

    @field_validator("cantidad_sembrada")
    @classmethod
    def cantidad_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cantidad_sembrada debe ser mayor que 0")
        return v

    @field_validator("peso_inicial_promedio_g")
    @classmethod
    def peso_no_negativo(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("peso_inicial_promedio_g debe ser >= 0")
        return v

    @model_validator(mode="after")
    def fecha_cierre_valida(self) -> "LoteCreate":
        if self.fecha_cierre and self.fecha_cierre < self.fecha_siembra:
            raise ValueError("fecha_cierre debe ser >= fecha_siembra")
        return self


class LoteUpdate(BaseModel):
    etapa_productiva_id: Optional[int] = None
    estado_id: Optional[int] = None
    fecha_cierre: Optional[date] = None
    observaciones: Optional[str] = None


class LoteOut(BaseModel):
    id: int
    codigo: str
    estanque_id: int
    especie_id: int
    etapa_productiva_id: int
    estado_id: int
    fecha_siembra: date
    fecha_cierre: Optional[date] = None
    cantidad_sembrada: int
    peso_inicial_promedio_g: Optional[float] = None
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Objetos relacionados
    especie: EspecieOut
    etapa_productiva: EtapaProductivaOut
    estado: EstadoLoteOut

    class Config:
        from_attributes = True
