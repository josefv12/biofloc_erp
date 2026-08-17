from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TipoAlarmaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = True


class TipoAlarmaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None


class TipoAlarmaOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class NivelAlarmaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    prioridad: int = Field(..., gt=0)


class NivelAlarmaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=30)
    prioridad: Optional[int] = Field(None, gt=0)


class NivelAlarmaOut(BaseModel):
    id: int
    nombre: str
    prioridad: int
    model_config = ConfigDict(from_attributes=True)


class EstadoAlarmaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=100)


class EstadoAlarmaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=100)


class EstadoAlarmaOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AlarmaCreate(BaseModel):
    tipo_alarma_id: int
    nivel_alarma_id: int
    estado_alarma_id: Optional[int] = None
    lote_id: Optional[int] = None
    equipo_id: Optional[int] = None
    evento_energia_id: Optional[int] = None
    fecha_hora: Optional[datetime] = None
    titulo: str = Field(..., min_length=1, max_length=150)
    mensaje: str = Field(..., min_length=1)
    observaciones: Optional[str] = None


class AlarmaUpdate(BaseModel):
    estado_alarma_id: Optional[int] = None
    observaciones: Optional[str] = None


class AlarmaOut(BaseModel):
    id: int
    tipo_alarma_id: int
    nivel_alarma_id: int
    estado_alarma_id: int
    lote_id: Optional[int] = None
    equipo_id: Optional[int] = None
    evento_energia_id: Optional[int] = None
    fecha_hora: datetime
    titulo: str
    mensaje: str
    atendida_por: Optional[int] = None
    fecha_atencion: Optional[datetime] = None
    observaciones: Optional[str] = None
    created_at: datetime
    tipo: TipoAlarmaOut
    nivel: NivelAlarmaOut
    estado: EstadoAlarmaOut
    model_config = ConfigDict(from_attributes=True)
