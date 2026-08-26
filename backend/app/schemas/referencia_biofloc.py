from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

INDICADORES_BIOFLOC = ("VOLUMEN_SEDIMENTABLE", "RELACION_CN")


class ReferenciaBioflocCreate(BaseModel):
    especie_id: int
    etapa_productiva_id: int
    indicador: str
    valor_minimo: Optional[Decimal] = None
    valor_objetivo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    unidad: Optional[str] = Field(None, max_length=30)
    observaciones: Optional[str] = None
    activo: bool = True

    @field_validator("indicador")
    @classmethod
    def indicador_conocido(cls, v: str) -> str:
        valor = v.strip().upper()
        if valor not in INDICADORES_BIOFLOC:
            raise ValueError("indicador debe ser VOLUMEN_SEDIMENTABLE o RELACION_CN")
        return valor

    @field_validator("unidad")
    @classmethod
    def unidad_trim(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        return valor or None

    @model_validator(mode="after")
    def validar_rangos(self) -> "ReferenciaBioflocCreate":
        if self.valor_minimo is not None and self.valor_maximo is not None:
            if self.valor_minimo > self.valor_maximo:
                raise ValueError("valor_minimo no puede ser mayor que valor_maximo")
        if (
            self.valor_objetivo is not None
            and self.valor_minimo is not None
            and self.valor_objetivo < self.valor_minimo
        ):
            raise ValueError("valor_objetivo no puede ser menor que valor_minimo")
        if (
            self.valor_objetivo is not None
            and self.valor_maximo is not None
            and self.valor_objetivo > self.valor_maximo
        ):
            raise ValueError("valor_objetivo no puede ser mayor que valor_maximo")
        return self


class ReferenciaBioflocUpdate(BaseModel):
    valor_minimo: Optional[Decimal] = None
    valor_objetivo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    unidad: Optional[str] = Field(None, max_length=30)
    observaciones: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("unidad")
    @classmethod
    def unidad_trim(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        return valor or None

    @model_validator(mode="after")
    def validar_rangos(self) -> "ReferenciaBioflocUpdate":
        if self.valor_minimo is not None and self.valor_maximo is not None:
            if self.valor_minimo > self.valor_maximo:
                raise ValueError("valor_minimo no puede ser mayor que valor_maximo")
        return self


class ReferenciaBioflocOut(BaseModel):
    id: int
    especie_id: int
    etapa_productiva_id: int
    indicador: str
    valor_minimo: Optional[Decimal] = None
    valor_objetivo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    unidad: Optional[str] = None
    observaciones: Optional[str] = None
    activo: bool

    model_config = ConfigDict(from_attributes=True)
