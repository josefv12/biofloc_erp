from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class MedicionAguaBase(BaseModel):
    lote_id: int
    parametro_id: int
    fecha_hora: datetime
    valor: Decimal = Field(..., ge=0)
    observaciones: Optional[str] = None

class MedicionAguaCreate(MedicionAguaBase):
    pass

class MedicionAguaOut(MedicionAguaBase):
    id: int
    registrado_por: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
