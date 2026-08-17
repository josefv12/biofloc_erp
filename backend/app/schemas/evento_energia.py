from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EventoEnergiaCreate(BaseModel):
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    duracion_minutos: Optional[int] = Field(None, ge=0)
    tipo: Optional[str] = Field("CORTE", min_length=1, max_length=50)
    respaldo_activado: Optional[bool] = False
    equipo_respaldo_id: Optional[int] = None
    observaciones: Optional[str] = None


class EventoEnergiaUpdate(BaseModel):
    fecha_hora_fin: Optional[datetime] = None
    duracion_minutos: Optional[int] = Field(None, ge=0)
    tipo: Optional[str] = Field(None, min_length=1, max_length=50)
    respaldo_activado: Optional[bool] = None
    equipo_respaldo_id: Optional[int] = None
    observaciones: Optional[str] = None


class EventoEnergiaOut(BaseModel):
    id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    duracion_minutos: Optional[int] = None
    tipo: str
    respaldo_activado: bool
    equipo_respaldo_id: Optional[int] = None
    observaciones: Optional[str] = None
    registrado_por: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
