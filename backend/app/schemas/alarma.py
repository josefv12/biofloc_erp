from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


CLASIF_NORMAL = "NORMAL"
CLASIF_STOCK_BAJO = "STOCK_BAJO"
CLASIF_SIN_STOCK = "SIN_STOCK"
CLASIFICACIONES = (CLASIF_NORMAL, CLASIF_STOCK_BAJO, CLASIF_SIN_STOCK)
CLASIF_GRAVEDAD = {CLASIF_SIN_STOCK: 0, CLASIF_STOCK_BAJO: 1, CLASIF_NORMAL: 2}


class AlarmaStockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    codigo: str
    nombre: str
    unidad: str
    stock_actual: Decimal = Field(max_digits=15, decimal_places=3)
    stock_minimo: Decimal = Field(max_digits=12, decimal_places=3)
    diferencia: Decimal = Field(max_digits=15, decimal_places=3)
    clasificacion: str
    activo: bool
    categoria_id: int
    categoria_nombre: Optional[str] = None
