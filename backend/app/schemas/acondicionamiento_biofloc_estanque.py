from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class AcondicionamientoBioflocEstanqueCreate(BaseModel):
    lote_id: int
    tipo_aplicacion_id: int
    producto_id: Optional[int] = None
    fecha_hora: datetime
    fecha_siembra_prevista: datetime | None = None
    cantidad: Optional[Decimal] = Field(None, ge=0)
    unidad: Optional[str] = Field(None, max_length=30)
    aireacion_activa: bool = True
    observaciones: Optional[str] = None

class AcondicionamientoBioflocEstanqueOut(AcondicionamientoBioflocEstanqueCreate):
    id: int
    estanque_id: int
    fecha_siembra_prevista: str
    registrado_por: int
    created_at: datetime
    stock_restante: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)
