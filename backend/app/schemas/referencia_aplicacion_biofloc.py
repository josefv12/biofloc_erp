from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

FASES_BIOFLOC = ("Inicio", "Levante", "Engorde")


class ReferenciaAplicacionBioflocCreate(BaseModel):
    especie_id: int
    semana: int = Field(..., gt=0)
    fase: str
    producto_id: int
    cantidad_referencia: Decimal = Field(..., ge=0)
    unidad: str = Field("kg", min_length=1, max_length=20)
    base_peces: int = Field(1100, gt=0)
    biomasa_objetivo_kg: Optional[Decimal] = Field(None, ge=0)
    observaciones: Optional[str] = None
    activo: bool = True

    @field_validator("fase")
    @classmethod
    def validar_fase(cls, value: str) -> str:
        value = value.strip()
        if value not in FASES_BIOFLOC:
            raise ValueError("fase debe ser Inicio, Levante o Engorde")
        return value

    @field_validator("unidad")
    @classmethod
    def validar_unidad(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("unidad no puede estar vacía")
        return value


class ReferenciaAplicacionBioflocUpdate(BaseModel):
    cantidad_referencia: Optional[Decimal] = Field(None, ge=0)
    unidad: Optional[str] = Field(None, min_length=1, max_length=20)
    base_peces: Optional[int] = Field(None, gt=0)
    biomasa_objetivo_kg: Optional[Decimal] = Field(None, ge=0)
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


class ReferenciaAplicacionBioflocOut(BaseModel):
    id: int
    especie_id: int
    semana: int
    fase: str
    producto_id: int
    cantidad_referencia: Decimal
    unidad: str
    base_peces: int
    biomasa_objetivo_kg: Optional[Decimal] = None
    observaciones: Optional[str] = None
    activo: bool

    model_config = ConfigDict(from_attributes=True)
