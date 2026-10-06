from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class AcondicionamientoBioflocEstanqueCreate(BaseModel):
    estanque_id: int
    tipo_aplicacion_id: int
    producto_id: Optional[int] = None
    fecha_hora: datetime
    fecha_siembra_prevista: date
    cantidad: Optional[Decimal] = Field(None, ge=0)
    unidad: Optional[str] = Field(None, max_length=30)
    aireacion_activa: bool = True
    observaciones: Optional[str] = None

class AcondicionamientoBioflocEstanqueOut(AcondicionamientoBioflocEstanqueCreate):
    id: int
    registrado_por: int
    created_at: datetime
    stock_restante: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)
