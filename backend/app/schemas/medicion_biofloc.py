from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class MedicionBioflocBase(BaseModel):
    lote_id: int
    fecha_hora: datetime
    volumen_sedimentable: Decimal = Field(..., ge=0)
    unidad: str = Field("mL/L", max_length=20)
    observaciones: Optional[str] = None
    relacion_cn: Optional[Decimal] = Field(None, ge=0)

class MedicionBioflocCreate(MedicionBioflocBase):
    pass

class MedicionBioflocOut(MedicionBioflocBase):
    id: int
    registrado_por: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
