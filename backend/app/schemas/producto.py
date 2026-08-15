from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductoBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre: str = Field(..., min_length=1, max_length=120)
    categoria_id: int
    unidad_id: int
    stock_minimo: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    activo: bool = True


class ProductoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=40)
    nombre: str = Field(..., min_length=1, max_length=120)
    categoria_id: int
    unidad_id: int
    stock_minimo: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    activo: Optional[bool] = True


class ProductoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=40)
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    categoria_id: Optional[int] = None
    unidad_id: Optional[int] = None
    stock_minimo: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    activo: Optional[bool] = None


class ProductoOut(ProductoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockProductoOut(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal

    model_config = ConfigDict(from_attributes=True)
