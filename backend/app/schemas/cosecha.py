from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class CosechaBase(BaseModel):
    lote_id: int
    fecha_hora: datetime
    cantidad_peces: int = Field(..., gt=0)
    peso_total_kg: Decimal = Field(..., gt=0)
    peso_promedio_g: Optional[Decimal] = Field(None, ge=0)
    observaciones: Optional[str] = None

class CosechaCreate(CosechaBase):
    pass

class CosechaOut(CosechaBase):
    id: int
    registrado_por: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
