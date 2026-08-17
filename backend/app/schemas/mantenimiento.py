from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TipoMantenimientoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=150)
    activo: Optional[bool] = True


class TipoMantenimientoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=150)
    activo: Optional[bool] = None


class TipoMantenimientoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class MantenimientoCreate(BaseModel):
    equipo_id: int
    tipo_mantenimiento_id: int
    fecha: date
    descripcion: str = Field(..., min_length=1, max_length=250)
    costo: Optional[Decimal] = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    proveedor: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None


class MantenimientoOut(BaseModel):
    id: int
    equipo_id: int
    tipo_mantenimiento_id: int
    fecha: date
    descripcion: str
    costo: Decimal
    proveedor: Optional[str] = None
    observaciones: Optional[str] = None
    registrado_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
