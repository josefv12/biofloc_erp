from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GastoBase(BaseModel):
    fecha: date
    categoria_id: int
    lote_id: Optional[int] = None
    estanque_id: Optional[int] = None
    descripcion: str = Field(..., min_length=1, max_length=250)
    valor: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    proveedor: Optional[str] = Field(None, max_length=150)
    observaciones: Optional[str] = None

    @model_validator(mode="after")
    def validar_destino(self):
        if self.lote_id is not None and self.estanque_id is not None:
            raise ValueError("Un costo debe asociarse a un lote o a un estanque, no a ambos")
        return self


class GastoCreate(GastoBase):
    pass


class GastoOut(GastoBase):
    id: int
    registrado_por: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
