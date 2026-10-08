from datetime import datetime
from pydantic import BaseModel, Field


class SiembraLoteCreate(BaseModel):
    producto_id: int = Field(..., gt=0, description="Producto de inventario que representa los alevinos")
    cantidad: int = Field(..., gt=0, description="Cantidad real de alevinos sembrados")
    fecha_hora: datetime
    peso_inicial_promedio_g: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class SiembraLoteOut(BaseModel):
    lote_id: int
    codigo: str
    producto_id: int
    cantidad_sembrada: int
    costo_unitario: float
    costo_total: float
    fecha_hora: datetime
    movimiento_inventario_id: int
