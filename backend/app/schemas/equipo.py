from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TipoEquipoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: bool = True


class TipoEquipoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = True


class TipoEquipoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None


class TipoEquipoOut(TipoEquipoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EstadoEquipoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=150)
    activo: bool = True


class EstadoEquipoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=150)
    activo: Optional[bool] = True


class EstadoEquipoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=150)
    activo: Optional[bool] = None


class EstadoEquipoOut(EstadoEquipoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EquipoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre: str = Field(..., min_length=1, max_length=120)
    tipo_equipo_id: int
    estado_id: int
    marca: Optional[str] = Field(None, max_length=80)
    modelo: Optional[str] = Field(None, max_length=80)
    numero_serie: Optional[str] = Field(None, max_length=100)
    fecha_adquisicion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = Field(None, ge=0, max_digits=14, decimal_places=2)
    ubicacion: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None
    activo: Optional[bool] = True


class EquipoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=40)
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    tipo_equipo_id: Optional[int] = None
    estado_id: Optional[int] = None
    marca: Optional[str] = Field(None, max_length=80)
    modelo: Optional[str] = Field(None, max_length=80)
    numero_serie: Optional[str] = Field(None, max_length=100)
    fecha_adquisicion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = Field(None, ge=0, max_digits=14, decimal_places=2)
    ubicacion: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


class EquipoOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo_equipo_id: int
    estado_id: int
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    valor_adquisicion: Optional[Decimal] = None
    ubicacion: Optional[str] = None
    observaciones: Optional[str] = None
    activo: bool
    created_at: datetime
    updated_at: datetime
    tipo: TipoEquipoOut
    estado: EstadoEquipoOut
    model_config = ConfigDict(from_attributes=True)
