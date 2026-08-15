from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class CategoriaInventarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: bool = True


class CategoriaInventarioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = True


class CategoriaInventarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None


class CategoriaInventarioOut(CategoriaInventarioBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
