from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ParametroAguaBase(BaseModel):
    nombre: str = Field(..., max_length=80)
    unidad: str = Field(..., max_length=30)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: bool = True

class ParametroAguaCreate(BaseModel):
    nombre: str = Field(..., max_length=80)
    unidad: str = Field(..., max_length=30)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = True

class ParametroAguaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=80)
    unidad: Optional[str] = Field(None, max_length=30)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None

class ParametroAguaOut(ParametroAguaBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
