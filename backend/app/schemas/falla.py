from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FallaCreate(BaseModel):
    equipo_id: int
    fecha_hora: datetime
    descripcion: str = Field(..., min_length=1, max_length=250)
    impacto: Optional[str] = Field(None, max_length=100)
    solucion: Optional[str] = None
    costo: Optional[Decimal] = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class FallaUpdate(BaseModel):
    descripcion: Optional[str] = Field(None, min_length=1, max_length=250)
    impacto: Optional[str] = Field(None, max_length=100)
    solucion: Optional[str] = None
    costo: Optional[Decimal] = Field(None, ge=0, max_digits=14, decimal_places=2)


class FallaOut(BaseModel):
    id: int
    equipo_id: int
    fecha_hora: datetime
    descripcion: str
    impacto: Optional[str] = None
    solucion: Optional[str] = None
    costo: Decimal
    registrada_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
