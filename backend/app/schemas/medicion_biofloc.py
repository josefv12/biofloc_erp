from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal

class MedicionBioflocBase(BaseModel):
    lote_id: Optional[int] = None
    estanque_id: Optional[int] = None
    fecha_hora: datetime
    volumen_sedimentable: Decimal = Field(..., ge=0)
    unidad: str = Field("mL/L", max_length=20)
    observaciones: Optional[str] = None
    relacion_cn: Optional[Decimal] = Field(None, ge=0)

    @model_validator(mode="after")
    def validar_contexto(self):
        if (self.lote_id is None) == (self.estanque_id is None):
            raise ValueError("Debe indicar exactamente un contexto: lote_id o estanque_id.")
        return self

class MedicionBioflocCreate(MedicionBioflocBase):
    pass

class MedicionBioflocOut(MedicionBioflocBase):
    id: int
    registrado_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
