from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


# ── Catálogo Estado ──────────────────────────────────────────────────────────

class EstadoEstanqueOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool

    class Config:
        from_attributes = True


# ── Estanque ─────────────────────────────────────────────────────────────────

class EstanqueCreate(BaseModel):
    codigo: str
    nombre: str
    diametro: float
    profundidad: float
    estado_id: int
    activo: bool = True

    @field_validator("diametro")
    @classmethod
    def diametro_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("diametro debe ser mayor que 0")
        return v

    @field_validator("profundidad")
    @classmethod
    def profundidad_positiva(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("profundidad debe ser mayor que 0")
        return v


class EstanqueUpdate(BaseModel):
    nombre: Optional[str] = None
    diametro: Optional[float] = None
    profundidad: Optional[float] = None
    estado_id: Optional[int] = None
    activo: Optional[bool] = None

    @field_validator("diametro")
    @classmethod
    def diametro_positivo(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("diametro debe ser mayor que 0")
        return v

    @field_validator("profundidad")
    @classmethod
    def profundidad_positiva(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("profundidad debe ser mayor que 0")
        return v


class EstanqueOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    diametro: float
    profundidad: float
    estado_id: int
    estado: EstadoEstanqueOut
    activo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
