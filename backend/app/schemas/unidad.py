from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class UnidadBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    simbolo: str = Field(..., min_length=1, max_length=10)
    activo: bool = True


class UnidadCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=30)
    simbolo: str = Field(..., min_length=1, max_length=10)
    activo: Optional[bool] = True


class UnidadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=30)
    simbolo: Optional[str] = Field(None, min_length=1, max_length=10)
    activo: Optional[bool] = None


class UnidadOut(UnidadBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
