from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class UnidadCantidadOut(BaseModel):
    unidad: str
    cantidad: Decimal = Field(..., max_digits=18, decimal_places=3)


class VentaFilaOut(BaseModel):
    venta_id: int
    detalle_id: int
    fecha: date
    cliente: Optional[str] = None
    lote_id: int
    lote_codigo: str
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    precio_unitario: Decimal = Field(..., max_digits=14, decimal_places=2)
    subtotal: Decimal = Field(..., max_digits=14, decimal_places=2)
    venta_total: Decimal = Field(..., max_digits=14, decimal_places=2)
    registrado_por: int
    registrado_por_nombre: Optional[str] = None


class ReporteVentasOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    suma_subtotales: Decimal = Field(..., max_digits=16, decimal_places=2)
    n_ventas: int
    filas: list[VentaFilaOut]


class CompraFilaOut(BaseModel):
    compra_id: int
    detalle_id: int
    fecha: date
    proveedor: Optional[str] = None
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    unidad: str
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    precio_unitario: Decimal = Field(..., max_digits=14, decimal_places=2)
    subtotal: Decimal = Field(..., max_digits=14, decimal_places=2)
    compra_total: Decimal = Field(..., max_digits=14, decimal_places=2)
    registrado_por: int
    registrado_por_nombre: Optional[str] = None


class ReporteComprasOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    suma_subtotales: Decimal = Field(..., max_digits=16, decimal_places=2)
    n_compras: int
    cantidad_por_unidad: list[UnidadCantidadOut]
    filas: list[CompraFilaOut]


class GastoFilaOut(BaseModel):
    gasto_id: int
    fecha: date
    categoria_id: int
    categoria: str
    descripcion: str
    proveedor: Optional[str] = None
    valor: Decimal = Field(..., max_digits=14, decimal_places=2)
    lote_id: Optional[int] = None
    lote_codigo: Optional[str] = None
    registrado_por: int
    registrado_por_nombre: Optional[str] = None


class ReporteGastosOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    total_valor: Decimal = Field(..., max_digits=16, decimal_places=2)
    filas: list[GastoFilaOut]


class InventarioFilaOut(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    unidad: str
    stock_actual: Decimal = Field(..., max_digits=15, decimal_places=3)
    stock_minimo: Decimal = Field(..., max_digits=12, decimal_places=3)
    clasificacion: str
    activo: bool
    categoria_id: int
    categoria_nombre: Optional[str] = None


class ReporteInventarioOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[InventarioFilaOut]


class MovimientoFilaOut(BaseModel):
    movimiento_id: int
    fecha_hora: datetime
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    unidad: str
    tipo: str
    afecta_stock: int
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    costo_unitario: Optional[Decimal] = Field(None, max_digits=14, decimal_places=2)
    costo_total: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)
    referencia_tipo: Optional[str] = None
    referencia_id: Optional[int] = None
    registrado_por: int
    registrado_por_nombre: Optional[str] = None


class ReporteMovimientosOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    suma_costo_total: Decimal = Field(..., max_digits=18, decimal_places=2)
    filas: list[MovimientoFilaOut]


class CompraInventarioFilaOut(BaseModel):
    compra_id: int
    detalle_id: int
    fecha: date
    proveedor: Optional[str] = None
    producto_id: int
    producto_codigo: str
    unidad: str
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    subtotal: Decimal = Field(..., max_digits=14, decimal_places=2)
    movimiento_id: Optional[int] = None
    referencia_tipo: Optional[str] = None
    tipo_movimiento: Optional[str] = None


class ReporteComprasInventarioOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[CompraInventarioFilaOut]


class ProduccionFilaOut(BaseModel):
    lote_id: int
    codigo: str
    estado: str
    estanque_codigo: str
    especie: str
    etapa: str
    fecha_siembra: date
    cantidad_sembrada: int
    mortalidad_acumulada: int
    peces_cosechados: int
    poblacion_estimada: int
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    ultima_biometria_fecha: Optional[datetime] = None
    peso_promedio_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)


class ReporteProduccionOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[ProduccionFilaOut]


class AguaFilaOut(BaseModel):
    medicion_id: int
    fecha_hora: datetime
    lote_id: int
    lote_codigo: str
    parametro: str
    unidad: str
    valor: Decimal = Field(..., max_digits=12, decimal_places=4)
    valor_minimo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    valor_maximo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fuera_de_rango: Optional[bool] = None
    registrado_por: int


class ReporteAguaOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    nota: str
    filas: list[AguaFilaOut]


class BioflocMedicionFilaOut(BaseModel):
    medicion_id: int
    fecha_hora: datetime
    lote_id: int
    lote_codigo: str
    volumen_sedimentable: Decimal = Field(..., max_digits=10, decimal_places=2)
    unidad: str
    relacion_cn: Optional[Decimal] = Field(None, max_digits=10, decimal_places=3)
    registrado_por: int


class BioflocAplicacionFilaOut(BaseModel):
    aplicacion_id: int
    fecha_hora: datetime
    lote_id: int
    lote_codigo: str
    tipo_aplicacion: str
    producto_id: Optional[int] = None
    cantidad: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    unidad: Optional[str] = None
    registrado_por: int


class ReporteBioflocOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    mediciones: list[BioflocMedicionFilaOut]
    aplicaciones: list[BioflocAplicacionFilaOut]


class AlimentacionFilaOut(BaseModel):
    alimentacion_id: int
    fecha_hora: datetime
    lote_id: int
    lote_codigo: str
    producto_id: int
    producto_codigo: str
    unidad: str
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    observaciones: Optional[str] = None
    registrado_por: int
    registrado_por_nombre: Optional[str] = None


class ReporteAlimentacionOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    cantidad_por_unidad: list[UnidadCantidadOut]
    filas: list[AlimentacionFilaOut]


class EquipoFilaOut(BaseModel):
    equipo_id: int
    codigo: str
    nombre: str
    tipo: str
    estado: str
    ubicacion: Optional[str] = None
    activo: bool


class ReporteEquiposOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[EquipoFilaOut]


class MantenimientoFilaOut(BaseModel):
    mantenimiento_id: int
    fecha: date
    equipo_id: int
    equipo_codigo: str
    tipo: str
    descripcion: str
    costo: Decimal = Field(..., max_digits=14, decimal_places=2)
    observaciones: Optional[str] = None
    registrado_por: int


class ReporteMantenimientosOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    total_costo: Decimal = Field(..., max_digits=16, decimal_places=2)
    filas: list[MantenimientoFilaOut]


class FallaFilaOut(BaseModel):
    falla_id: int
    fecha_hora: datetime
    equipo_id: int
    equipo_codigo: str
    descripcion: str
    impacto: Optional[str] = None
    solucion: Optional[str] = None
    costo: Decimal = Field(..., max_digits=14, decimal_places=2)
    registrada_por: int


class ReporteFallasOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    total_costo: Decimal = Field(..., max_digits=16, decimal_places=2)
    filas: list[FallaFilaOut]


class EnergiaFilaOut(BaseModel):
    evento_id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    tipo: str
    duracion_minutos: Optional[int] = None
    respaldo_activado: bool
    equipo_respaldo_id: Optional[int] = None
    observaciones: Optional[str] = None
    registrado_por: Optional[int] = None


class ReporteEnergiaOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[EnergiaFilaOut]


class AlarmaFilaOut(BaseModel):
    alarma_id: int
    fecha_hora: datetime
    tipo: str
    nivel: str
    estado: str
    titulo: str
    mensaje: str
    equipo_id: Optional[int] = None
    equipo_codigo: Optional[str] = None
    lote_id: Optional[int] = None
    lote_codigo: Optional[str] = None
    evento_energia_id: Optional[int] = None
    atendida_por: Optional[int] = None
    fecha_atencion: Optional[datetime] = None


class ReporteAlarmasOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    total_registros: int
    generado_en: datetime
    filas: list[AlarmaFilaOut]
