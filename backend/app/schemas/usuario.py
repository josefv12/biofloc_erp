from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RolOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    correo: str
    rol_id: int
    rol: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    correo: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8, max_length=72)
    rol_id: int
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        valor = v.strip()
        if not valor:
            raise ValueError("nombre no puede estar vacío")
        return valor

    @field_validator("correo")
    @classmethod
    def correo_normalizado(cls, v: str) -> str:
        valor = v.strip().lower()
        if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
            raise ValueError("correo inválido")
        return valor

    @field_validator("password")
    @classmethod
    def password_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("password no puede estar vacío")
        if len(v) < 8:
            raise ValueError("password debe tener al menos 8 caracteres")
        return v


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    correo: Optional[str] = Field(None, min_length=3, max_length=150)
    password: Optional[str] = Field(None, min_length=8, max_length=72)
    rol_id: Optional[int] = None
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valor = v.strip()
        if not valor:
            raise ValueError("nombre no puede estar vacío")
        return valor

    @field_validator("correo")
    @classmethod
    def correo_normalizado(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valor = v.strip().lower()
        if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
            raise ValueError("correo inválido")
        return valor

    @field_validator("password")
    @classmethod
    def password_si_viene(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip() or len(v) < 8:
            raise ValueError("password debe tener al menos 8 caracteres")
        return v
