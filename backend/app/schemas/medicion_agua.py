from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal

class MedicionAguaBase(BaseModel):
    lote_id: Optional[int] = None
    estanque_id: Optional[int] = None
    parametro_id: int
    fecha_hora: datetime
    valor: Decimal = Field(..., ge=0)
    observaciones: Optional[str] = None

    @model_validator(mode="after")
    def validar_contexto(self):
        if (self.lote_id is None) == (self.estanque_id is None):
            raise ValueError("Debe indicar exactamente un contexto: lote_id o estanque_id.")
        return self

class MedicionAguaCreate(MedicionAguaBase):
    pass

class MedicionAguaOut(MedicionAguaBase):
    id: int
    registrado_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
