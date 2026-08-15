from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class TipoAplicacionBioflocBase(BaseModel):
    nombre: str = Field(..., max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: bool = True

class TipoAplicacionBioflocCreate(BaseModel):
    nombre: str = Field(..., max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = True

class TipoAplicacionBioflocUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None

class TipoAplicacionBioflocOut(TipoAplicacionBioflocBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
