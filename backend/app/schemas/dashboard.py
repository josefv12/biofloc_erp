from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class PeriodoOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class TotalNOut(BaseModel):
    n: int
    total: Decimal = Field(..., max_digits=16, decimal_places=2)


class NombreNOut(BaseModel):
    nombre: str
    n: int


class NombreTotalOut(BaseModel):
    nombre: str
    n: int
    total: Decimal = Field(..., max_digits=16, decimal_places=2)


class UnidadStockOut(BaseModel):
    unidad: str
    n_productos: int
    stock: Decimal = Field(..., max_digits=18, decimal_places=3)


class UnidadMovimientoOut(BaseModel):
    unidad: str
    n: int
    cantidad: Decimal = Field(..., max_digits=18, decimal_places=3)
    costo: Decimal = Field(..., max_digits=18, decimal_places=2)


class LoteVentaOut(BaseModel):
    lote_id: int
    codigo: str
    n: int
    cantidad: Decimal = Field(..., max_digits=18, decimal_places=3)
    subtotal: Decimal = Field(..., max_digits=16, decimal_places=2)


class UltimaBiometriaOut(BaseModel):
    lote_id: int
    codigo: str
    fecha_hora: Optional[str] = None
    peso_promedio_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)


class DashboardResumenOut(BaseModel):
    periodo: PeriodoOut
    ventas: TotalNOut
    gastos: TotalNOut
    compras: TotalNOut
    productos_activos: int
    productos_sin_stock: int
    productos_stock_bajo: int
    alarmas_pendientes: int
    equipos_activos: int
    equipos_operativos: int
    mantenimientos_periodo: int
    eventos_energia_periodo: int
    lotes_activos: int


class DashboardInventarioOut(BaseModel):
    periodo: PeriodoOut
    productos_activos: int
    productos_inactivos: int
    productos_sin_stock: int
    productos_stock_bajo: int
    productos_normal: int
    stock_por_unidad: list[UnidadStockOut]
    entradas: list[UnidadMovimientoOut]
    salidas: list[UnidadMovimientoOut]
    n_entradas: int
    n_salidas: int
    costo_entradas: Decimal = Field(..., max_digits=18, decimal_places=2)
    costo_salidas: Decimal = Field(..., max_digits=18, decimal_places=2)


class DashboardComprasOut(BaseModel):
    periodo: PeriodoOut
    n_compras: int
    total: Decimal = Field(..., max_digits=16, decimal_places=2)
    promedio: Decimal = Field(..., max_digits=16, decimal_places=2)
    top_proveedores: list[NombreTotalOut]
    productos_distintos: int
    cantidad_por_unidad: list[UnidadStockOut]


class DashboardVentasOut(BaseModel):
    periodo: PeriodoOut
    n_ventas: int
    total: Decimal = Field(..., max_digits=16, decimal_places=2)
    ticket_promedio: Decimal = Field(..., max_digits=16, decimal_places=2)
    cantidad_vendida: Decimal = Field(..., max_digits=18, decimal_places=3)
    top_clientes: list[NombreTotalOut]
    por_lote: list[LoteVentaOut]


class DashboardGastosOut(BaseModel):
    periodo: PeriodoOut
    n_gastos: int
    total: Decimal = Field(..., max_digits=16, decimal_places=2)
    promedio: Decimal = Field(..., max_digits=16, decimal_places=2)
    por_categoria: list[NombreTotalOut]
    asociados_a_lote: TotalNOut
    top_proveedores: list[NombreTotalOut]


class DashboardEquiposOut(BaseModel):
    periodo: PeriodoOut
    n_equipos: int
    n_activos: int
    por_estado: list[NombreNOut]
    por_tipo: list[NombreNOut]
    mantenimientos_periodo: TotalNOut
    fallas_periodo: TotalNOut
    equipos_con_fallas_periodo: int


class DashboardEnergiaOut(BaseModel):
    periodo: PeriodoOut
    n_eventos: int
    n_abiertos: int
    n_respaldo_activado: int
    duracion_minutos_cerrados: int
    por_tipo: list[NombreNOut]


class DashboardAlarmasOut(BaseModel):
    periodo: PeriodoOut
    snapshot_por_estado: list[NombreNOut]
    snapshot_por_nivel: list[NombreNOut]
    snapshot_por_tipo: list[NombreNOut]
    snapshot_con_equipo: int
    snapshot_con_evento_energia: int
    snapshot_con_lote: int
    creadas_periodo: int
    creadas_por_tipo: list[NombreNOut]
    creadas_por_nivel: list[NombreNOut]


class DashboardProduccionOut(BaseModel):
    periodo: PeriodoOut
    lotes_por_estado: list[NombreNOut]
    estanques_por_estado: list[NombreNOut]
    lotes_activos: int
    poblacion_estimada_activos: int
    supervivencia_pct_activos: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    supervivencia_pct_activos_motivo: Optional[str] = None
    alimentaciones_periodo: int
    alimentacion_por_unidad: list[UnidadStockOut]
    cosechas_periodo: int
    cosechas_peces: int
    cosechas_peso_total_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    mortalidades_periodo: int
    mortalidades_peces: int
    mediciones_agua_periodo: int
    mediciones_agua_fuera_rango: int
    mediciones_biofloc_periodo: int
    aplicaciones_biofloc_periodo: int
    ultimas_biometrias: list[UltimaBiometriaOut]
