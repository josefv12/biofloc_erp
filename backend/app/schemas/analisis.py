from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.lote import EspecieOut, EtapaProductivaOut, EstadoLoteOut
from app.schemas.referencia_produccion import ReferenciaProduccionOut
from app.schemas.alimentacion_referencia import (
    AlimentacionComparativaPuntoOut,
    ReferenciaAlimentacionActivaOut,
)


class AnalisisEstanqueOut(BaseModel):
    id: int
    codigo: str
    nombre: str


class AnalisisLoteOut(BaseModel):
    id: int
    codigo: str
    fecha_siembra: date
    fecha_cierre: Optional[date] = None
    cantidad_sembrada: int
    peso_inicial_promedio_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=3)
    estado: EstadoLoteOut


class IndicadoresLoteOut(BaseModel):
    peces_sembrados: int
    mortalidad_acumulada: int
    peces_cosechados: int
    poblacion_estimada: int
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    ultima_biometria_id: Optional[int] = None
    peso_promedio_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    talla_promedio: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    unidad_talla: Optional[str] = None
    fecha_ultima_biometria: Optional[datetime] = None
    peso_inicial_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=3)
    dias_cultivo: int
    semana_cultivo: int
    ganancia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    ganancia_diaria_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=6)
    biomasa_inicial_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    biomasa_actual_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    alimento_real_acumulado_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    fca: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fca_disponible: bool
    fca_motivo: Optional[str] = None
    sgr_pct_dia: Optional[Decimal] = Field(None, max_digits=14, decimal_places=4)
    densidad_kg_m3: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    volumen_util_m3: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    racion_diaria_recomendada_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=4)
    numero_raciones_diarias: Optional[int] = None
    semana_productiva_alimentacion: Optional[int] = None
    biomasa_esperada_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    raciones_diarias_texto: Optional[str] = None
    racion_por_comida_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    racion_basada_en_peso: Optional[str] = None


class DefinicionesCalculoOut(BaseModel):
    zona_horaria: str
    dias_cultivo: str
    semana_cultivo: str
    unidad_masa_productiva: str
    biomasa_inicial_kg: str
    biomasa_actual_kg: str
    ganancia_peso_g: str
    ganancia_diaria_g: str
    alimento_real_acumulado_kg: str
    fca: str
    referencia_produccion: str
    racion_diaria_recomendada_kg: str
    numero_raciones_diarias: str
    poblacion_as_of: str
    serie_biomasa: str
    serie_fca: str
    alimento_convertible_kg: str
    estadisticas: str
    mediana: str
    variacion_porcentual: str
    comparacion_real_objetivo: str
    filtros_fecha: str
    estado_analitico: str
    cumplimiento_rango: str
    recomendaciones: str


class StatsSerieOut(BaseModel):
    """Estadística descriptiva de una serie numérica. Sin diagnóstico."""

    unidad: Optional[str] = None
    n: int
    primero: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    ultimo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    promedio: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    minimo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    maximo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    mediana: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    variacion_porcentual: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)
    variacion_motivo: Optional[str] = None


class ComparacionRealObjetivoOut(BaseModel):
    """Comparación descriptiva contra un objetivo del modelo de datos."""

    real: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    objetivo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    unidad: Optional[str] = None
    diferencia: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    diferencia_porcentaje: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)
    motivo: Optional[str] = None


class EstadoAnalitico(str, Enum):
    """Estado reusable. ALERTA/CRITICO requieren umbrales formales."""

    NORMAL = "NORMAL"
    ALERTA = "ALERTA"
    CRITICO = "CRITICO"
    SIN_REFERENCIA = "SIN_REFERENCIA"
    SIN_DATOS = "SIN_DATOS"


class CumplimientoRango(str, Enum):
    """Cumplimiento objetivo separado de la severidad analítica."""

    DENTRO_RANGO = "DENTRO_RANGO"
    FUERA_RANGO = "FUERA_RANGO"
    NO_EVALUABLE = "NO_EVALUABLE"


class EvaluacionIndicadorOut(BaseModel):
    """REAL + OBJETIVO/RANGO + desviación + explicación, sin juicios."""

    indicador: str
    etiqueta: str
    real: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    objetivo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    minimo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    maximo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    unidad: Optional[str] = None
    diferencia_objetivo: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    diferencia_objetivo_porcentaje: Optional[Decimal] = Field(
        None, max_digits=16, decimal_places=2
    )
    desviacion_rango: Optional[Decimal] = Field(None, max_digits=24, decimal_places=6)
    desviacion_rango_porcentaje: Optional[Decimal] = Field(
        None, max_digits=16, decimal_places=2
    )
    estado_analitico: Optional[EstadoAnalitico] = None
    cumplimiento_rango: CumplimientoRango = CumplimientoRango.NO_EVALUABLE
    motivo: Optional[str] = None
    explicacion: str
    referencia: Optional[str] = None
    fecha_real: Optional[date] = None
    fecha_referencia: Optional[date] = None


class RecomendacionAnaliticaOut(BaseModel):
    """Recomendación trazable; no crea una alarma del ERP."""

    indicador: str
    estado_analitico: Optional[EstadoAnalitico] = None
    cumplimiento_rango: CumplimientoRango
    motivo: str
    recomendacion: str


class BiometriaSerieOut(BaseModel):
    id: int
    fecha_hora: datetime
    cantidad_muestra: int
    peso_total_muestra_g: Decimal = Field(..., max_digits=12, decimal_places=3)
    peso_promedio_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    talla_promedio: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    unidad_talla: Optional[str] = None
    semana_cultivo: int
    referencia_id: Optional[int] = None
    peso_esperado_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    diferencia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    diferencia_peso_pct: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)


class MortalidadSerieOut(BaseModel):
    id: int
    fecha_hora: datetime
    cantidad: int
    acumulada: int
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)


class PoblacionPuntoOut(BaseModel):
    """Población reconstruida a la fecha del evento (as-of)."""

    fecha_hora: datetime
    evento: str
    mortalidad_acumulada: int
    peces_cosechados: int
    poblacion_estimada: int
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)


class BiomasaPuntoOut(BaseModel):
    fecha_hora: datetime
    biometria_id: int
    poblacion_estimada: int
    peso_promedio_g: Decimal = Field(..., max_digits=14, decimal_places=3)
    biomasa_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    ganancia_biomasa_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)


class FcaPuntoOut(BaseModel):
    fecha_hora: datetime
    biometria_id: int
    alimento_real_acumulado_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    biomasa_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    ganancia_biomasa_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    fca: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fca_disponible: bool
    fca_motivo: Optional[str] = None


class CrecimientoPuntoOut(BaseModel):
    """Ganancia individual reconstruida en cada biometría."""

    fecha_hora: datetime
    biometria_id: int
    dias_cultivo: int
    peso_promedio_g: Decimal = Field(..., max_digits=14, decimal_places=3)
    ganancia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    ganancia_diaria_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=6)
    motivo: Optional[str] = None


class ReferenciaSemanaOut(BaseModel):
    semana_cultivo: int
    referencia_id: Optional[int] = None
    peso_esperado_g: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    tasa_alimentacion_pct: Optional[Decimal] = Field(None, max_digits=6, decimal_places=3)
    motivo: Optional[str] = None


class AguaMedicionOut(BaseModel):
    id: int
    parametro_id: int
    parametro: str
    unidad: str
    valor: Decimal = Field(..., max_digits=12, decimal_places=4)
    fecha_hora: datetime
    valor_minimo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    valor_maximo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fuera_de_rango: Optional[bool] = None
    registrado_por: Optional[int] = None
    registrado_por_nombre: Optional[str] = None


class BioflocMedicionOut(BaseModel):
    id: int
    fecha_hora: datetime
    volumen_sedimentable: Decimal = Field(..., max_digits=10, decimal_places=2)
    unidad: str
    relacion_cn: Optional[Decimal] = Field(None, max_digits=10, decimal_places=3)
    registrado_por: Optional[int] = None
    registrado_por_nombre: Optional[str] = None


class AlimentoUnidadOut(BaseModel):
    unidad: str
    cantidad: Decimal = Field(..., max_digits=18, decimal_places=3)


class AlimentoRegistroOut(BaseModel):
    id: int
    fecha_hora: datetime
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    unidad: str
    cantidad: Decimal = Field(..., max_digits=12, decimal_places=3)
    cantidad_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    acumulado_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    convertible_a_kg: bool


class AguaParametroEstadisticasOut(BaseModel):
    parametro_id: int
    parametro: str
    unidad: str
    valor_minimo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    valor_maximo: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    con_referencia: bool
    fuera_de_rango_n: Optional[int] = None
    fuera_de_rango_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    estadisticas: StatsSerieOut


class EstadisticasAnalisisOut(BaseModel):
    peso_promedio_g: StatsSerieOut
    talla_promedio: StatsSerieOut
    biomasa_kg: StatsSerieOut
    poblacion_estimada: StatsSerieOut
    supervivencia_porcentaje: StatsSerieOut
    mortalidad_acumulada: StatsSerieOut
    alimento_acumulado_kg: StatsSerieOut
    fca: StatsSerieOut
    volumen_sedimentable: StatsSerieOut
    relacion_cn: StatsSerieOut
    agua: list[AguaParametroEstadisticasOut]


class ComparacionesAnalisisOut(BaseModel):
    peso_g: ComparacionRealObjetivoOut


class ProductividadLoteOut(BaseModel):
    """Cuánto produce el lote; no mide uso de recursos."""

    biomasa_actual_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    ganancia_biomasa_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    peso_cosechado_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    peces_cosechados: int
    ganancia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    ganancia_diaria_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=6)
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    motivos: dict[str, str]


class EficienciaLoteOut(BaseModel):
    """Uso de recursos disponible sin inventar objetivos ni costos."""

    fca: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fca_disponible: bool
    fca_motivo: Optional[str] = None
    alimento_real_acumulado_kg: Optional[Decimal] = Field(
        None, max_digits=18, decimal_places=3
    )
    ganancia_biomasa_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    desviacion_peso_porcentaje: Optional[Decimal] = Field(
        None, max_digits=16, decimal_places=2
    )
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    costo_por_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    costo_por_kg_motivo: str
    costo_alimentacion: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    costo_alimentacion_motivo: str


class FinanzasLoteOut(BaseModel):
    """Importes directamente trazables al lote; no son rentabilidad completa."""

    ingresos_lote: Decimal = Field(..., max_digits=18, decimal_places=2)
    ventas_registradas: int
    gastos_directos_lote: Decimal = Field(..., max_digits=18, decimal_places=2)
    gastos_registrados: int
    costos_completos: bool
    costos_completos_motivo: str
    utilidad: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    utilidad_motivo: str
    margen_porcentaje: Optional[Decimal] = Field(None, max_digits=16, decimal_places=2)
    margen_motivo: str


class FiltrosAnalisisOut(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    nota: str


class AnalisisLoteCompletoOut(BaseModel):
    lote: AnalisisLoteOut
    estanque: AnalisisEstanqueOut
    especie: EspecieOut
    etapa: EtapaProductivaOut
    definiciones: DefinicionesCalculoOut
    filtros: FiltrosAnalisisOut
    indicadores: IndicadoresLoteOut
    pendientes: dict[str, str]
    referencia_produccion: Optional[ReferenciaProduccionOut] = None
    referencias_por_semana: list[ReferenciaSemanaOut]
    comparaciones: ComparacionesAnalisisOut
    evaluaciones: list[EvaluacionIndicadorOut]
    recomendaciones: list[RecomendacionAnaliticaOut]
    productividad: ProductividadLoteOut
    eficiencia: EficienciaLoteOut
    finanzas: FinanzasLoteOut
    estadisticas: EstadisticasAnalisisOut
    biometrias: list[BiometriaSerieOut]
    mortalidades: list[MortalidadSerieOut]
    serie_poblacion: list[PoblacionPuntoOut]
    serie_biomasa: list[BiomasaPuntoOut]
    serie_crecimiento: list[CrecimientoPuntoOut]
    serie_fca: list[FcaPuntoOut]
    agua: list[AguaMedicionOut]
    agua_serie: list[AguaMedicionOut]
    biofloc: Optional[BioflocMedicionOut] = None
    biofloc_serie: list[BioflocMedicionOut]
    alimentacion_real_por_unidad: list[AlimentoUnidadOut]
    alimentacion_real: list[AlimentoRegistroOut]
    referencia_alimentacion: Optional[ReferenciaAlimentacionActivaOut] = None
    serie_alimentacion_comparativa: list[AlimentacionComparativaPuntoOut] = []


# --- Comparativo por estanque (nivel granja) -------------------------------


class CicloComparativoOut(BaseModel):
    lote_id: int
    lote_codigo: str
    estanque_id: int
    estanque_codigo: str
    especie: str
    etapa: str
    estado_lote: str
    fecha_siembra: date
    fecha_cierre: Optional[date] = None
    dias_cultivo: int
    semana_cultivo: int
    productividad: ProductividadLoteOut
    eficiencia: EficienciaLoteOut
    finanzas: FinanzasLoteOut


class EstanqueComparativoOut(BaseModel):
    estanque_id: int
    codigo: str
    nombre: str
    activo: bool
    lote_id: Optional[int] = None
    lote_codigo: Optional[str] = None
    especie: Optional[str] = None
    etapa: Optional[str] = None
    fecha_siembra: Optional[date] = None
    dias_cultivo: Optional[int] = None
    semana_cultivo: Optional[int] = None
    peces_sembrados: Optional[int] = None
    poblacion_estimada: Optional[int] = None
    peso_promedio_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    biomasa_actual_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    fca: Optional[Decimal] = Field(None, max_digits=12, decimal_places=4)
    fca_disponible: bool = False
    fca_motivo: Optional[str] = None
    agua_parametros_medidos: int = 0
    agua_parametros_con_referencia: int = 0
    agua_parametros_fuera_de_rango: Optional[int] = None
    ganancia_peso_g: Optional[Decimal] = Field(None, max_digits=14, decimal_places=3)
    alimento_real_acumulado_kg: Optional[Decimal] = Field(
        None, max_digits=18, decimal_places=3
    )
    productividad: Optional[ProductividadLoteOut] = None
    eficiencia: Optional[EficienciaLoteOut] = None
    finanzas: Optional[FinanzasLoteOut] = None
    estado_biofloc: EstadoAnalitico = EstadoAnalitico.SIN_DATOS
    sin_lote_activo_motivo: Optional[str] = None


class ResumenGranjaOut(BaseModel):
    estanques: int
    estanques_con_lote_activo: int
    peces_sembrados: int
    poblacion_estimada: int
    mortalidad_acumulada: int
    biomasa_actual_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    lotes_sin_biomasa: int
    supervivencia_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    mortalidad_porcentaje: Optional[Decimal] = Field(None, max_digits=8, decimal_places=2)
    lotes_con_fca: int
    fca: Optional[Decimal] = None
    fca_motivo: str
    alimento_real_acumulado_kg: Optional[Decimal] = Field(None, max_digits=18, decimal_places=3)
    lotes_sin_alimento: int
    peso_cosechado_kg: Decimal = Field(..., max_digits=18, decimal_places=3)
    peces_cosechados: int
    ingresos_lotes_activos: Decimal = Field(..., max_digits=18, decimal_places=2)
    gastos_directos_lotes_activos: Decimal = Field(..., max_digits=18, decimal_places=2)
    utilidad: Optional[Decimal] = None
    utilidad_motivo: str


class ComparativoEstanquesOut(BaseModel):
    definiciones: dict[str, str]
    resumen: ResumenGranjaOut
    estanques: list[EstanqueComparativoOut]
    ciclos: list[CicloComparativoOut] = []
