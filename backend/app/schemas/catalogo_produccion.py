from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EspecieCreate(BaseModel):
    nombre_comun: str = Field(..., min_length=1, max_length=100)
    nombre_cientifico: Optional[str] = Field(None, max_length=150)
    activo: bool = True

    @field_validator("nombre_comun")
    @classmethod
    def nombre_comun_no_vacio(cls, v: str) -> str:
        valor = v.strip()
        if not valor:
            raise ValueError("nombre_comun no puede estar vacío")
        return valor

    @field_validator("nombre_cientifico")
    @classmethod
    def nombre_cientifico_trim(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        return valor or None


class EspecieUpdate(BaseModel):
    nombre_comun: Optional[str] = Field(None, min_length=1, max_length=100)
    nombre_cientifico: Optional[str] = Field(None, max_length=150)
    activo: Optional[bool] = None

    @field_validator("nombre_comun")
    @classmethod
    def nombre_comun_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valor = v.strip()
        if not valor:
            raise ValueError("nombre_comun no puede estar vacío")
        return valor

    @field_validator("nombre_cientifico")
    @classmethod
    def nombre_cientifico_trim(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valor = v.strip()
        return valor or None


class EspecieCatalogoOut(BaseModel):
    id: int
    nombre_comun: str
    nombre_cientifico: Optional[str] = None
    activo: bool
    n_referencias_produccion: int = 0
    n_referencias_agua: int = 0

    model_config = ConfigDict(from_attributes=True)


class EtapaProductivaCatalogoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    orden: int
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class EstadoLoteCatalogoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool

    model_config = ConfigDict(from_attributes=True)
