from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional
from decimal import Decimal

class ReferenciaAguaBase(BaseModel):
    especie_id: int
    etapa_productiva_id: int
    parametro_id: int
    valor_minimo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    observaciones: Optional[str] = None
    activo: bool = True

class ReferenciaAguaCreate(BaseModel):
    especie_id: int
    etapa_productiva_id: int
    parametro_id: int
    valor_minimo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    observaciones: Optional[str] = None
    activo: Optional[bool] = True

    @model_validator(mode="after")
    def validar_rangos(self):
        if self.valor_minimo is not None and self.valor_maximo is not None:
            if self.valor_minimo > self.valor_maximo:
                raise ValueError("valor_minimo no puede ser mayor que valor_maximo")
        return self

class ReferenciaAguaUpdate(BaseModel):
    valor_minimo: Optional[Decimal] = None
    valor_maximo: Optional[Decimal] = None
    observaciones: Optional[str] = None
    activo: Optional[bool] = None

    @model_validator(mode="after")
    def validar_rangos(self):
        if self.valor_minimo is not None and self.valor_maximo is not None:
            if self.valor_minimo > self.valor_maximo:
                raise ValueError("valor_minimo no puede ser mayor que valor_maximo")
        return self

class ReferenciaAguaOut(ReferenciaAguaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
