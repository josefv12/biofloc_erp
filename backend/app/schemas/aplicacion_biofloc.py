from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class AplicacionBioflocBase(BaseModel):
    lote_id: int
    tipo_aplicacion_id: int
    producto_id: Optional[int] = None
    fecha_hora: datetime
    cantidad: Optional[Decimal] = Field(None, ge=0)
    unidad: Optional[str] = Field(None, max_length=30)
    observaciones: Optional[str] = None

class AplicacionBioflocCreate(AplicacionBioflocBase):
    pass

class AplicacionBioflocOut(AplicacionBioflocBase):
    id: int
    registrado_por: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
