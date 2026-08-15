from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal


class TipoMovimientoInventarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=150)
    afecta_stock: Literal[-1, 1]


class TipoMovimientoInventarioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=150)
    afecta_stock: Literal[-1, 1]


class TipoMovimientoInventarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=150)
    afecta_stock: Optional[Literal[-1, 1]] = None


class TipoMovimientoInventarioOut(TipoMovimientoInventarioBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
