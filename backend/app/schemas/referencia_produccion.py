from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FASES_ALIMENTACION = ("Inicio", "Levante", "Engorde")


def _validar_raciones(minimo: Optional[int], maximo: Optional[int]) -> None:
    if minimo is not None and minimo < 0:
        raise ValueError("raciones_min debe ser >= 0")
    if maximo is not None and minimo is not None and maximo < minimo:
        raise ValueError("raciones_max no puede ser menor que raciones_min")


class ReferenciaProduccionCreate(BaseModel):
    especie_id: int
    etapa_productiva_id: int
    semana_desde: int = Field(..., ge=0)
    semana_hasta: int = Field(..., ge=0)
    peso_esperado_g: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, ge=0, max_digits=6, decimal_places=3)
    raciones_min: Optional[int] = Field(None, ge=0)
    raciones_max: Optional[int] = Field(None, ge=0)
    fase: Optional[str] = Field(None, max_length=40)
    observaciones: Optional[str] = None
    activo: bool = True

    @field_validator("fase")
    @classmethod
    def fase_conocida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        if not valor:
            return None
        if valor not in FASES_ALIMENTACION:
            raise ValueError("fase debe ser Inicio, Levante o Engorde")
        return valor

    @model_validator(mode="after")
    def rango_semanal(self) -> "ReferenciaProduccionCreate":
        if self.semana_hasta < self.semana_desde:
            raise ValueError("semana_hasta debe ser >= semana_desde")
        _validar_raciones(self.raciones_min, self.raciones_max)
        return self


class ReferenciaProduccionUpdate(BaseModel):
    especie_id: Optional[int] = None
    etapa_productiva_id: Optional[int] = None
    semana_desde: Optional[int] = Field(None, ge=0)
    semana_hasta: Optional[int] = Field(None, ge=0)
    peso_esperado_g: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, ge=0, max_digits=6, decimal_places=3)
    raciones_min: Optional[int] = Field(None, ge=0)
    raciones_max: Optional[int] = Field(None, ge=0)
    fase: Optional[str] = Field(None, max_length=40)
    observaciones: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("fase")
    @classmethod
    def fase_conocida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        if not valor:
            return None
        if valor not in FASES_ALIMENTACION:
            raise ValueError("fase debe ser Inicio, Levante o Engorde")
        return valor

    @model_validator(mode="after")
    def rango_semanal(self) -> "ReferenciaProduccionUpdate":
        if (
            self.semana_desde is not None
            and self.semana_hasta is not None
            and self.semana_hasta < self.semana_desde
        ):
            raise ValueError("semana_hasta debe ser >= semana_desde")
        _validar_raciones(self.raciones_min, self.raciones_max)
        return self


class ReferenciaProduccionOut(BaseModel):
    id: int
    especie_id: int
    etapa_productiva_id: int
    semana_desde: int
    semana_hasta: int
    peso_esperado_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, max_digits=6, decimal_places=3)
    raciones_min: Optional[int] = None
    raciones_max: Optional[int] = None
    fase: Optional[str] = None
    observaciones: Optional[str] = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
