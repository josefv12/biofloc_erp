from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal

class MedicionAguaBase(BaseModel):
    lote_id: int
    parametro_id: int
    fecha_hora: datetime
    valor: Decimal = Field(..., ge=0)
    observaciones: str | None = None

class MedicionAguaCreate(MedicionAguaBase):
    pass

class MedicionAguaOut(MedicionAguaBase):
    id: int
    registrado_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
