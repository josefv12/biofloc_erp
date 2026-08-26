from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FilaReferenciaAlimentacionOut(BaseModel):
    semana: int
    fase: str
    peso_esperado_g: Decimal = Field(..., max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Decimal = Field(..., max_digits=6, decimal_places=3)
    raciones_diarias: str
    raciones_min: int
    raciones_max: int
    numero_raciones_diarias: Optional[int] = None
    alimento_referencia_1000_peces_kg: Decimal = Field(..., max_digits=18, decimal_places=3)


class TablaReferenciaAlimentacionOut(BaseModel):
    version: str
    especie: str
    semanas: int
    base_peces_referencia: int
    nota: str
    filas: list[FilaReferenciaAlimentacionOut]


class ReferenciaAlimentacionActivaOut(BaseModel):
    semana_productiva: int
    fase: Optional[str] = None
    peso_esperado_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    peso_real_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    peso_inicial_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=3)
    peso_operativo_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    peso_para_racion_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    basada_en_peso: Optional[str] = None
    peso_utilizado: Optional[str] = None
    diferencia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=2)
    poblacion_estimada: int
    biomasa_esperada_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    biomasa_para_racion_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, max_digits=6, decimal_places=3)
    raciones_diarias: Optional[str] = None
    raciones_min: Optional[int] = None
    raciones_max: Optional[int] = None
    numero_raciones_diarias: Optional[int] = None
    racion_diaria_recomendada_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    racion_diaria_recomendada_g: Optional[Decimal] = Field(None, max_digits=18, decimal_places=1)
    racion_por_comida_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    racion_por_comida_g: Optional[Decimal] = Field(None, max_digits=18, decimal_places=1)
    racion_por_comida_min_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    racion_por_comida_max_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    racion_por_comida_min_g: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    racion_por_comida_max_g: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    alimento_referencia_1000_peces_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    fuente: str
    referencia_bd_id: Optional[int] = None


class ContextoAlimentacionLoteOut(BaseModel):
    lote_id: int
    referencia_activa: Optional[ReferenciaAlimentacionActivaOut] = None
    motivo: Optional[str] = None


class AlimentacionComparativaPuntoOut(BaseModel):
    fecha: str
    real_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    recomendada_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    desviacion_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    desviacion_porcentaje: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)
    semana_cultivo: int
