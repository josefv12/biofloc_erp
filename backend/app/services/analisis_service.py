"""Capa de cálculo del núcleo analítico (lote y comparativo por estanque).

Toda la lógica analítica vive aquí: el frontend solo presenta lo que este
servicio entrega.

Unidad canónica de masa (declarada en el DDL con COMMENT ON COLUMN):
  g  → lotes.peso_inicial_promedio_g, biometrias.peso_total_muestra_g,
       cosechas.peso_promedio_g, referencias_produccion.peso_esperado_g
  kg → cosechas.peso_total_kg, biomasa, alimento para FCA

La conversión g → kg se hace en un único punto (MIL para pesos, FACTOR_A_KG
para alimento). No se mezclan gramos y kilogramos en una misma suma.

Cuando un indicador no se puede calcular se devuelve None y la razón técnica
queda en el mapa `pendientes`. Nunca se devuelve NaN, Infinity ni un valor
inventado.

Las series históricas (población, biomasa, supervivencia, alimento acumulado y
FCA) reconstruyen el estado a la fecha de cada evento con las mismas fórmulas
congeladas del indicador puntual: no se repite el valor actual en todas las
fechas ni se interpola.
"""
import logging
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text
from fastapi import HTTPException

from app.models.cosecha import Cosecha
from app.models.lote import Lote
from app.models.parametro_agua import ParametroAgua
from app.models.referencia_agua import ReferenciaAgua
from app.models.referencia_biofloc import ReferenciaBiofloc
from app.models.referencia_produccion import ReferenciaProduccion
from app.schemas.analisis import (
    AguaMedicionOut,
    AguaParametroEstadisticasOut,
    AlimentoRegistroOut,
    AlimentoUnidadOut,
    AnalisisEstanqueOut,
    AnalisisLoteCompletoOut,
    AnalisisLoteOut,
    BiomasaPuntoOut,
    BiometriaSerieOut,
    BioflocMedicionOut,
    ComparacionRealObjetivoOut,
    ComparacionesAnalisisOut,
    ComparativoEstanquesOut,
    CrecimientoPuntoOut,
    CicloComparativoOut,
    DefinicionesCalculoOut,
    EficienciaLoteOut,
    EstadoAnalitico,
    EstadisticasAnalisisOut,
    EstanqueComparativoOut,
    EvaluacionIndicadorOut,
    FcaPuntoOut,
    FiltrosAnalisisOut,
    FinanzasLoteOut,
    IndicadoresLoteOut,
    MortalidadSerieOut,
    PoblacionPuntoOut,
    ProductividadLoteOut,
    ReferenciaSemanaOut,
    RecomendacionAnaliticaOut,
    ResumenGranjaOut,
    StatsSerieOut,
)
from app.schemas.lote import EspecieOut, EtapaProductivaOut, EstadoLoteOut
from app.schemas.referencia_produccion import ReferenciaProduccionOut
from app.services import estadistica_service as est_svc
from app.services import evaluacion_analitica_service as eval_svc
from app.services import referencia_produccion_service as ref_svc
from app.services import alimentacion_referencia_service as alim_ref_svc
from app.schemas.alimentacion_referencia import (
    AlimentacionComparativaPuntoOut,
    ReferenciaAlimentacionActivaOut,
)
from app.config.referencia_alimentacion_tilapia import semana_productiva_alimentacion
from app.services.indicadores_lote import (
    MOTIVO_COSECHA_SIN_PESO,
    MOTIVO_SIN_PESO_INICIAL,
    biomasa_kg,
    densidad_kg_m3 as dens_oficial,
    ganancia_biomasa_productiva_kg,
    ganancia_diaria_g as gpd_oficial,
    mortalidad_pct,
    sgr_pct_dia,
    supervivencia_biologica_pct,
    volumen_estanque_m3,
)
from app.services.poblacion_lote import calcular_poblacion_disponible, obtener_salidas_peces

TZ = ZoneInfo("America/Bogota")
D2 = Decimal("0.01")
D3 = Decimal("0.001")
D4 = Decimal("0.0001")
CIEN = Decimal("100")
MIL = Decimal("1000")

# Factores hacia kg para las unidades de masa declaradas en `unidades.simbolo`.
FACTOR_A_KG = {"kg": Decimal("1"), "g": Decimal("0.001")}

logger = logging.getLogger(__name__)

RAZON_SIN_BIOMETRIA = "SIN_BIOMETRIA"
RAZON_SIN_PESO_INICIAL = "SIN_PESO_INICIAL_LOTE"
RAZON_DIAS_CERO = "DIAS_CULTIVO_CERO"
RAZON_SIN_ALIMENTO = "SIN_ALIMENTO_REAL_REGISTRADO"
RAZON_ALIMENTO_UNIDAD = "UNIDAD_ALIMENTO_INCOMPATIBLE"
RAZON_POBLACION_NEGATIVA = "POBLACION_NEGATIVA_HISTORICA"

# Motivos de FCA no disponible (contrato de la fase).
FCA_SIN_BIOMASA_INICIAL = "SIN_BIOMASA_INICIAL"
FCA_SIN_BIOMASA_FINAL = "SIN_BIOMASA_FINAL"
FCA_GANANCIA_NO_POSITIVA = "GANANCIA_BIOMASA_NO_POSITIVA"

RAZON_SIN_REFERENCIA = "SIN_REFERENCIA_PRODUCCION_APLICABLE"
RAZON_SIN_TASA = "REFERENCIA_SIN_TASA_ALIMENTACION"
RAZON_SIN_RACIONES = "SIN_CONFIGURACION_DE_RACIONES"
RAZON_SIN_PESO_ESPERADO = "REFERENCIA_SIN_PESO_ESPERADO"
RAZON_OBJETIVO_CERO = "OBJETIVO_CERO"
RAZON_SIN_LOTE_ACTIVO = "SIN_LOTE_ACTIVO"
RAZON_FCA_GRANJA = "SIN_REGLA_DE_AGREGACION_DE_FCA"
RAZON_COSTOS_INCOMPLETOS = "COSTOS_INCOMPLETOS_SIN_PRORRATEOS"
RAZON_COSTO_ALIMENTO = "ALIMENTACION_SIN_COSTO_UNITARIO_TRAZABLE"
RAZON_UTILIDAD = "UTILIDAD_NO_DISPONIBLE_POR_COSTOS_INCOMPLETOS"

DEFINICIONES = DefinicionesCalculoOut(
    zona_horaria="America/Bogota",
    dias_cultivo=(
        "fecha_fin = fecha_cierre si el lote está cerrado; si no, la fecha de hoy en "
        "America/Bogota. dias_cultivo = max(0, fecha_fin - fecha_siembra) en días "
        "calendario. fecha_siembra es obligatoria en el DDL, por lo que siempre se "
        "puede calcular."
    ),
    semana_cultivo=(
        "Edad del lote desde la siembra (no semana ISO). "
        "semana = floor(días_cultivo / 7) + 1: día 0–6 = semana 1, día 7–13 = semana 2, "
        "día 14 = semana 3. El backend es la única fuente; el frontend no recalcula."
    ),
    unidad_masa_productiva=(
        "g para peso individual y peso de muestra de biometría; kg para peso total de "
        "cosecha, biomasa y alimento del FCA. Declarado en el DDL con COMMENT ON COLUMN."
    ),
    biomasa_inicial_kg="cantidad_sembrada × peso_inicial_promedio_g / 1000.",
    biomasa_actual_kg="poblacion_estimada × peso_promedio_g de la última biometría / 1000. N/D sin biometría; nunca 0 inventado.",
    ganancia_peso_g="peso_promedio_g de la última biometría − peso_inicial_promedio_g del lote.",
    ganancia_diaria_g="ganancia_peso_g / dias_cultivo. N/D si dias_cultivo <= 0.",
    alimento_real_acumulado_kg=(
        "Suma del alimento realmente suministrado al lote, convertido a kg solo desde "
        "unidades de masa ('g', 'kg'). Si alguna alimentación está en una unidad que no "
        "es de masa, no se suma nada y el total queda en null."
    ),
    fca=(
        "FCA acumulado (económico): kg de alimento real suministrado por cada kg de "
        "biomasa neta producida. "
        "alimento_real_acumulado_kg / ganancia_biomasa_productiva_kg. "
        "ganancia_biomasa_productiva = biomasa_actual + biomasa_cosechada − biomasa_inicial "
        "cuando la cosecha tiene peso_total_kg. Sin peso de cosecha no se inventa. "
        "Usa exclusivamente alimento real del lote; nunca inventario. "
        "Desde la siembra hasta la fecha de análisis; si el lote está cerrado, hasta el cierre. "
        "El alimento permanece en el numerador aunque haya mortalidades; una mayor mortalidad "
        "puede aumentar el FCA. No es FCA biológico, ni por etapa, ni por intervalo. "
        "FCA esperado: sin referencia oficial configurada."
    ),
    referencia_produccion=(
        "Se resuelve por especie + semana_cultivo sobre referencias_produccion activas "
        "(semana_desde <= semana <= semana_hasta). La etapa del lote solo desempata. "
        "Una sola fuente: no hay fallback a Python. Si no hay fila, N/D."
    ),
    racion_diaria_recomendada_kg=(
        "biomasa_operativa_kg × tasa_alimentacion_pct / 100. "
        "Biomasa operativa = población viva (sembrados − mortalidad − cosecha) × peso_operativo_g / 1000. "
        "Peso operativo = última biometría válida; si no hay, peso inicial de siembra. "
        "El peso esperado de la referencia es guía/comparación; no entra en la ración. "
        "Tasa y raciones de la referencia de esa especie y semana."
    ),
    numero_raciones_diarias=(
        "Raciones/día de la referencia de la semana. Si es un rango (6–8) se muestra el rango "
        "y la cantidad por ración como intervalo (diario/raciones_max … diario/raciones_min); "
        "no se usa el promedio."
    ),
    poblacion_as_of=(
        "Población a la fecha de un evento: cantidad_sembrada − mortalidades con "
        "fecha_hora <= la fecha del evento − peces cosechados con fecha_hora <= la fecha "
        "del evento. El punto de siembra se ubica a las 00:00 de America/Bogota de "
        "fecha_siembra. Solo se generan puntos donde hay siembra, mortalidad, cosecha o "
        "biometría: no se inventa población diaria."
    ),
    serie_biomasa=(
        "Por cada biometría: población as-of de esa fecha × peso_promedio_g de esa "
        "biometría / 1000. ganancia_biomasa_kg = biomasa del punto + biomasa cosechada "
        "hasta esa fecha − biomasa_inicial_kg."
    ),
    serie_fca=(
        "Evolución del FCA acumulado: por cada biometría, alimento real acumulado en kg "
        "hasta esa fecha / ganancia de biomasa acumulada hasta esa fecha. "
        "No es un FCA de intervalo entre biometrías. Si la ganancia es <= 0, o falta biomasa "
        "inicial, o el alimento no es convertible a kg, el punto queda en null con su "
        "motivo. No se arrastra el FCA final hacia atrás."
    ),
    alimento_convertible_kg=(
        "cantidad_kg solo existe para unidades de masa ('g', 'kg'); en L, mL o und queda "
        "en null y no se asume densidad. acumulado_kg suma únicamente lo convertible y "
        "pasa a null desde el primer registro no convertible, igual que el indicador."
    ),
    estadisticas=est_svc.DEFINICION_ESTADISTICAS,
    mediana=est_svc.DEFINICION_MEDIANA,
    variacion_porcentual=est_svc.DEFINICION_VARIACION,
    comparacion_real_objetivo=(
        "diferencia = real − objetivo; diferencia_porcentaje = (real − objetivo) / "
        "objetivo × 100, null si el objetivo es 0. Es descriptivo: no clasifica el "
        "resultado como bueno ni malo."
    ),
    filtros_fecha=(
        "fecha_desde y fecha_hasta son opcionales y recortan únicamente las series "
        "devueltas y sus estadísticas, comparando la fecha en America/Bogota de forma "
        "inclusiva. Los indicadores, los acumulados y las series as-of se calculan "
        "siempre con todo el historial desde la siembra, para no alterar las fórmulas."
    ),
    estado_analitico=(
        "NORMAL, ALERTA, CRITICO, SIN_REFERENCIA o SIN_DATOS. ALERTA y CRITICO "
        "solo pueden usarse si existen zonas de severidad formalmente configuradas; "
        "el modelo actual no contiene esas zonas."
    ),
    cumplimiento_rango=(
        "DENTRO_RANGO, FUERA_RANGO o NO_EVALUABLE. Es independiente del estado "
        "analítico: una medición fuera de rango no se convierte automáticamente en "
        "ALERTA o CRITICO."
    ),
    recomendaciones=(
        "Solo se generan desde DATOS → REGLA → CUMPLIMIENTO. En esta fase únicamente "
        "el agua fuera de un rango configurado justifica revisar la medición y el "
        "control operativo según el protocolo; nunca crea una alarma del ERP."
    ),
)

DEFINICIONES_COMPARATIVO = {
    "alcance": (
        "Un renglón por estanque con su lote ACTIVO. Los indicadores son los mismos del "
        "análisis por lote, calculados con las fórmulas congeladas; no se recalculan aquí."
    ),
    "sin_lote_activo": (
        "Si el estanque no tiene lote ACTIVO, todos los indicadores quedan en null con "
        "motivo SIN_LOTE_ACTIVO."
    ),
    "supervivencia_granja": (
        "Suma de (sembrados − mortalidad) / suma de cantidades sembradas × 100 sobre los "
        "lotes activos. La cosecha no entra en la supervivencia biológica."
    ),
    "mortalidad_granja": (
        "Suma de mortalidades acumuladas / suma de cantidades sembradas × 100 sobre los "
        "lotes activos incluidos."
    ),
    "biomasa_granja": (
        "Suma de las biomasas actuales disponibles. lotes_sin_biomasa indica cuántos "
        "lotes activos no aportan biomasa por falta de biometría."
    ),
    "alimento_granja": (
        "Suma del alimento real acumulado (kg) de los lotes activos donde el backend "
        "pudo convertirlo a kg. lotes_sin_alimento indica cuántos lotes no aportan "
        "ese total. No es un nuevo cálculo de ración ni de FCA."
    ),
    "fca_granja": (
        "N/D: actualmente no existe una regla oficial para agregar el FCA de varios lotes "
        "(por biomasa, por alimento o promedio simple). No se inventa un promedio. "
        "Se informa cuántos lotes tienen FCA acumulado disponible. El FCA pertenece al lote, "
        "no al estanque."
    ),
    "estado_agua": (
        "Cuenta de parámetros con última medición, de cuántos tienen referencia para la "
        "especie y etapa del lote, y de cuántos están fuera de rango. No hay semáforos."
    ),
}


def _d2(v) -> Decimal:
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _d3(v) -> Decimal:
    return Decimal(str(v)).quantize(D3, rounding=ROUND_HALF_UP)


def _d2n(v) -> Optional[Decimal]:
    return None if v is None else _d2(v)


def _d3n(v) -> Optional[Decimal]:
    return None if v is None else _d3(v)


def _d4n(v) -> Optional[Decimal]:
    if v is None:
        return None
    return Decimal(str(v)).quantize(D4, rounding=ROUND_HALF_UP)


def _i(v) -> int:
    return int(v or 0)


def _hoy_bogota() -> date:
    return datetime.now(TZ).date()


def _dias_semana(fecha_siembra: date, fecha_fin: date) -> tuple[int, int]:
    """Días de cultivo y semana: floor(días / 7) + 1. Día 0–6 = semana 1."""
    dias = (fecha_fin - fecha_siembra).days
    if dias < 0:
        dias = 0
    semana = semana_productiva_alimentacion(dias)
    return dias, semana


def _dias_y_semana(fecha_siembra: date, fecha_cierre: Optional[date]) -> tuple[int, int]:
    fecha_fin = fecha_cierre if fecha_cierre is not None else _hoy_bogota()
    return _dias_semana(fecha_siembra, fecha_fin)


def _fecha_local(momento: datetime) -> date:
    """Fecha en America/Bogota de un instante almacenado con zona."""
    if momento.tzinfo is None:
        return momento.date()
    return momento.astimezone(TZ).date()


SQL_ULTIMA_BIOMETRIA_LOTE = """
SELECT id, fecha_hora,
       ROUND(peso_total_muestra_g / NULLIF(cantidad_muestra, 0), 3) AS peso_promedio_g,
       talla_promedio, unidad_talla
FROM biometrias
WHERE lote_id = :lote_id
ORDER BY fecha_hora DESC, id DESC
LIMIT 1
"""


def elegir_ultima_biometria(filas: list[dict]) -> Optional[dict]:
    """Misma regla que SQL_ULTIMA_BIOMETRIA_LOTE: fecha_hora DESC, id DESC."""
    validas = [fila for fila in filas if fila.get("fecha_hora") is not None and fila.get("id") is not None]
    if not validas:
        return None
    return max(validas, key=lambda fila: (fila["fecha_hora"], fila["id"]))


def _porcentaje(parte: int, total: int) -> Optional[Decimal]:
    if total <= 0:
        return None
    return _d2(Decimal(parte) / Decimal(total) * CIEN)


def _alimento_kg(por_unidad: list[AlimentoUnidadOut]) -> tuple[Optional[Decimal], Optional[str]]:
    """Suma el alimento real en kg. Devuelve (kg, razón si no es convertible)."""
    if not por_unidad:
        return None, RAZON_SIN_ALIMENTO
    total = Decimal("0")
    for fila in por_unidad:
        factor = FACTOR_A_KG.get(fila.unidad)
        if factor is None:
            return None, RAZON_ALIMENTO_UNIDAD
        total += Decimal(str(fila.cantidad)) * factor
    return total.quantize(D3, rounding=ROUND_HALF_UP), None


def _fca_oficial(
    alimento_kg: Optional[Decimal],
    razon_alimento: Optional[str],
    ganancia: Optional[Decimal],
    motivo_ganancia: Optional[str],
) -> tuple[Optional[Decimal], Optional[str]]:
    """alimento / ganancia productiva. Nunca divide por 0 ni por ganancia negativa."""
    if ganancia is None:
        if motivo_ganancia == MOTIVO_SIN_PESO_INICIAL:
            return None, FCA_SIN_BIOMASA_INICIAL
        if motivo_ganancia == MOTIVO_COSECHA_SIN_PESO:
            return None, MOTIVO_COSECHA_SIN_PESO
        return None, FCA_SIN_BIOMASA_FINAL
    if alimento_kg is None or alimento_kg <= 0:
        return None, razon_alimento or RAZON_SIN_ALIMENTO
    if ganancia <= 0:
        return None, FCA_GANANCIA_NO_POSITIVA
    return (alimento_kg / ganancia).quantize(D4, rounding=ROUND_HALF_UP), None


def _comparacion(
    real: Optional[Decimal],
    objetivo: Optional[Decimal],
    unidad: str,
    motivo_sin_real: str,
    motivo_sin_objetivo: str,
) -> ComparacionRealObjetivoOut:
    """real vs objetivo con diferencia absoluta y porcentual. Sin diagnóstico."""
    if real is None:
        return ComparacionRealObjetivoOut(objetivo=objetivo, unidad=unidad, motivo=motivo_sin_real)
    if objetivo is None:
        return ComparacionRealObjetivoOut(real=real, unidad=unidad, motivo=motivo_sin_objetivo)
    diferencia = real - objetivo
    if objetivo == 0:
        return ComparacionRealObjetivoOut(
            real=real,
            objetivo=objetivo,
            unidad=unidad,
            diferencia=diferencia,
            motivo=RAZON_OBJETIVO_CERO,
        )
    return ComparacionRealObjetivoOut(
        real=real,
        objetivo=objetivo,
        unidad=unidad,
        diferencia=diferencia,
        diferencia_porcentaje=(diferencia / objetivo * CIEN).quantize(D2, rounding=ROUND_HALF_UP),
    )


# --- Contexto de indicadores (compartido por lote y comparativo) ------------


@dataclass
class _Contexto:
    sembrados: int
    mortalidad_acumulada: int
    cosechados: int
    poblacion: int
    dias: int
    semana: int
    peso_inicial_g: Optional[Decimal]
    peso_promedio_g: Optional[Decimal]
    biomasa_inicial_kg: Optional[Decimal]
    biomasa_actual_kg: Optional[Decimal]
    biomasa_cosechada_kg: Decimal
    ganancia_biomasa_kg: Optional[Decimal]
    alimento_por_unidad: list[AlimentoUnidadOut]
    alimento_kg: Optional[Decimal]
    razon_alimento: Optional[str]
    referencia: Optional[ReferenciaProduccion]
    referencia_alimentacion: Optional[ReferenciaAlimentacionActivaOut]
    indicadores: IndicadoresLoteOut
    pendientes: dict[str, str]


def _bloques_productivos(
    db: Session, lote: Lote, ctx: _Contexto
) -> tuple[ProductividadLoteOut, EficienciaLoteOut, FinanzasLoteOut]:
    """Deriva bloques V1 únicamente desde datos directamente trazables."""
    cosecha = db.execute(
        text(
            """
            SELECT COALESCE(SUM(cantidad_peces), 0) AS peces,
                   COALESCE(SUM(peso_total_kg), 0) AS peso_kg
            FROM cosechas WHERE lote_id = :lote_id
            """
        ),
        {"lote_id": lote.id},
    ).mappings().one()
    finanzas = db.execute(
        text(
            """
            SELECT
              (SELECT COUNT(DISTINCT dv.venta_id)
                 FROM detalles_venta dv WHERE dv.lote_id = :lote_id) AS ventas_n,
              (SELECT COALESCE(SUM(dv.subtotal), 0)
                 FROM detalles_venta dv WHERE dv.lote_id = :lote_id) AS ingresos,
              (SELECT COUNT(*) FROM gastos g WHERE g.lote_id = :lote_id) AS gastos_n,
              (SELECT COALESCE(SUM(g.valor), 0)
                 FROM gastos g WHERE g.lote_id = :lote_id) AS gastos
            """
        ),
        {"lote_id": lote.id},
    ).mappings().one()

    motivos_productividad: dict[str, str] = {}
    if ctx.biomasa_actual_kg is None:
        motivos_productividad["biomasa_actual_kg"] = ctx.pendientes.get(
            "biomasa_actual_kg", RAZON_SIN_BIOMETRIA
        )
    ganancia_biomasa, motivo_ganancia = ganancia_biomasa_productiva_kg(
        ctx.biomasa_actual_kg,
        ctx.biomasa_inicial_kg,
        ctx.biomasa_cosechada_kg,
        hay_cosecha=ctx.cosechados > 0,
        cosecha_con_peso=ctx.biomasa_cosechada_kg > 0,
    )
    if ganancia_biomasa is None and motivo_ganancia:
        motivos_productividad["ganancia_biomasa_kg"] = motivo_ganancia
    elif ganancia_biomasa is None:
        motivos_productividad["ganancia_biomasa_kg"] = (
            FCA_SIN_BIOMASA_INICIAL
            if ctx.biomasa_inicial_kg is None
            else FCA_SIN_BIOMASA_FINAL
        )

    peso_objetivo = (
        _d2n(ctx.referencia_alimentacion.peso_esperado_g)
        if ctx.referencia_alimentacion is not None
        else None
    )
    desviacion_peso = None
    if ctx.peso_promedio_g is not None and peso_objetivo not in (None, Decimal("0")):
        desviacion_peso = (
            (ctx.peso_promedio_g - peso_objetivo) / peso_objetivo * CIEN
        ).quantize(D2, rounding=ROUND_HALF_UP)

    productividad = ProductividadLoteOut(
        biomasa_actual_kg=ctx.biomasa_actual_kg,
        ganancia_biomasa_kg=ganancia_biomasa,
        peso_cosechado_kg=_d3(cosecha["peso_kg"]),
        peces_cosechados=_i(cosecha["peces"]),
        ganancia_peso_g=ctx.indicadores.ganancia_peso_g,
        ganancia_diaria_g=ctx.indicadores.ganancia_diaria_g,
        supervivencia_porcentaje=ctx.indicadores.supervivencia_porcentaje,
        mortalidad_porcentaje=ctx.indicadores.mortalidad_porcentaje,
        motivos=motivos_productividad,
    )
    eficiencia = EficienciaLoteOut(
        fca=ctx.indicadores.fca,
        fca_disponible=ctx.indicadores.fca_disponible,
        fca_motivo=ctx.indicadores.fca_motivo,
        alimento_real_acumulado_kg=ctx.indicadores.alimento_real_acumulado_kg,
        ganancia_biomasa_kg=ganancia_biomasa,
        desviacion_peso_porcentaje=desviacion_peso,
        supervivencia_porcentaje=ctx.indicadores.supervivencia_porcentaje,
        mortalidad_porcentaje=ctx.indicadores.mortalidad_porcentaje,
        costo_por_kg=None,
        costo_por_kg_motivo=RAZON_COSTOS_INCOMPLETOS,
        costo_alimentacion=None,
        costo_alimentacion_motivo=RAZON_COSTO_ALIMENTO,
    )
    finanzas_lote = FinanzasLoteOut(
        ingresos_lote=Decimal(str(finanzas["ingresos"])).quantize(D2),
        ventas_registradas=_i(finanzas["ventas_n"]),
        gastos_directos_lote=Decimal(str(finanzas["gastos"])).quantize(D2),
        gastos_registrados=_i(finanzas["gastos_n"]),
        costos_completos=False,
        costos_completos_motivo=RAZON_COSTOS_INCOMPLETOS,
        utilidad=None,
        utilidad_motivo=RAZON_UTILIDAD,
        margen_porcentaje=None,
        margen_motivo=RAZON_UTILIDAD,
    )
    return productividad, eficiencia, finanzas_lote


def _evaluar_biofloc(
    db: Session,
    lote: Lote,
    *,
    indicador: str,
    etiqueta: str,
    real,
    unidad: Optional[str],
    fecha_real,
):
    """Contrasta medición Biofloc con la referencia digitada, si existe.

    No inventa C:N ni sólidos. Si el administrador no configuró rango ni
    objetivo, se mantiene SIN_REFERENCIA_BIOFLOC.
    """
    codigo = "VOLUMEN_SEDIMENTABLE" if indicador == "volumen_sedimentable" else "RELACION_CN"
    ref = (
        db.query(ReferenciaBiofloc)
        .filter(
            ReferenciaBiofloc.especie_id == lote.especie_id,
            ReferenciaBiofloc.etapa_productiva_id == lote.etapa_productiva_id,
            ReferenciaBiofloc.indicador == codigo,
            ReferenciaBiofloc.activo.is_(True),
        )
        .first()
    )
    minimo = _d4n(ref.valor_minimo) if ref else None
    maximo = _d4n(ref.valor_maximo) if ref else None
    objetivo = _d4n(ref.valor_objetivo) if ref else None
    unidad_ref = (ref.unidad if ref and ref.unidad else unidad)
    if minimo is not None or maximo is not None:
        evaluacion = eval_svc.evaluar_rango(
            indicador=indicador,
            etiqueta=etiqueta,
            real=real,
            minimo=minimo,
            maximo=maximo,
            objetivo=objetivo,
            unidad=unidad_ref,
            fecha_real=fecha_real,
        )
    else:
        evaluacion = eval_svc.evaluar_objetivo(
            indicador=indicador,
            etiqueta=etiqueta,
            real=real,
            objetivo=objetivo,
            unidad=unidad_ref,
            fecha_real=fecha_real,
            motivo_sin_referencia="SIN_REFERENCIA_BIOFLOC",
        )
    return evaluacion


def _evaluaciones_agua_catalogo(
    db: Session,
    lote: Lote,
    agua: list[AguaMedicionOut],
    ya_evaluadas: list,
) -> list:
    """Completa parámetros del catálogo sin medición. No pisa agua:{id} ya evaluado."""
    vistos = {ev.indicador for ev in ya_evaluadas}
    mediciones = {m.parametro_id for m in agua}
    refs = {
        int(r.parametro_id): r
        for r in db.query(ReferenciaAgua)
        .filter(
            ReferenciaAgua.especie_id == lote.especie_id,
            ReferenciaAgua.etapa_productiva_id == lote.etapa_productiva_id,
            ReferenciaAgua.activo.is_(True),
        )
        .all()
    }
    extras = []
    parametros = (
        db.query(ParametroAgua)
        .filter(ParametroAgua.activo.is_(True))
        .order_by(ParametroAgua.id)
        .all()
    )
    for parametro in parametros:
        clave = f"agua:{parametro.id}"
        if clave in vistos or parametro.id in mediciones:
            continue
        ref = refs.get(int(parametro.id))
        extras.append(
            eval_svc.evaluar_rango(
                indicador=clave,
                etiqueta=parametro.nombre,
                real=None,
                minimo=_d4n(ref.valor_minimo) if ref else None,
                maximo=_d4n(ref.valor_maximo) if ref else None,
                unidad=parametro.unidad,
                referencia=(
                    f"{lote.especie.nombre_comun} / {lote.etapa_productiva.nombre} / {parametro.nombre}"
                    if ref
                    else None
                ),
            )
        )
    return extras


def _construir_evaluaciones(
    *,
    db: Session,
    lote: Lote,
    ctx: _Contexto,
    agua: list[AguaMedicionOut],
    biofloc: Optional[BioflocMedicionOut],
    alimentacion: list[AlimentoRegistroOut],
) -> tuple[list[EvaluacionIndicadorOut], list[RecomendacionAnaliticaOut]]:
    """Construye estados explicables desde valores ya calculados.

    No recalcula fórmulas productivas ni crea alarmas. La comparación diaria
    de alimento usa el último día con registros y la ración recomendada actual,
    exponiendo ambas fechas para que la diferencia temporal sea visible.
    """
    evaluaciones: list[EvaluacionIndicadorOut] = []
    recomendaciones: list[RecomendacionAnaliticaOut] = []

    peso_catalogo = (
        _d2n(ctx.referencia_alimentacion.peso_esperado_g)
        if ctx.referencia_alimentacion is not None
        else None
    )
    referencia_peso = (
        f"{lote.especie.nombre_comun} / semana {ctx.semana} / "
        f"referencia #{ctx.referencia_alimentacion.referencia_bd_id}"
        if ctx.referencia_alimentacion is not None and ctx.referencia_alimentacion.referencia_bd_id
        else None
    )
    evaluaciones.append(
        eval_svc.evaluar_objetivo(
            indicador="peso_promedio_g",
            etiqueta="Peso promedio",
            real=ctx.peso_promedio_g,
            objetivo=peso_catalogo,
            unidad="g",
            referencia=referencia_peso,
            fecha_real=(
                _fecha_local(ctx.indicadores.fecha_ultima_biometria)
                if ctx.indicadores.fecha_ultima_biometria
                else None
            ),
            fecha_referencia=_hoy_bogota() if peso_catalogo is not None else None,
            motivo_sin_datos=RAZON_SIN_BIOMETRIA,
            motivo_sin_referencia=(
                RAZON_SIN_REFERENCIA if ctx.referencia_alimentacion is None else RAZON_SIN_PESO_ESPERADO
            ),
        )
    )

    if agua:
        for medicion in agua:
            evaluacion = eval_svc.evaluar_rango(
                indicador=f"agua:{medicion.parametro_id}",
                etiqueta=medicion.parametro,
                real=medicion.valor,
                minimo=medicion.valor_minimo,
                maximo=medicion.valor_maximo,
                unidad=medicion.unidad,
                referencia=(
                    f"{lote.especie.nombre_comun} / {lote.etapa_productiva.nombre} / "
                    f"{medicion.parametro}"
                    if medicion.fuera_de_rango is not None
                    else None
                ),
                fecha_real=_fecha_local(medicion.fecha_hora),
            )
            evaluaciones.append(evaluacion)
            recomendacion = eval_svc.recomendacion_agua(evaluacion)
            if recomendacion is not None:
                recomendaciones.append(recomendacion)
    else:
        evaluaciones.append(
            eval_svc.evaluar_rango(
                indicador="agua",
                etiqueta="Agua",
                real=None,
                minimo=None,
                maximo=None,
                unidad=None,
            )
        )

    evaluaciones.extend(_evaluaciones_agua_catalogo(db, lote, agua, evaluaciones))

    fecha_alimento: Optional[date] = None
    alimento_diario: Optional[Decimal] = None
    motivo_alimento = RAZON_SIN_ALIMENTO
    if alimentacion:
        fecha_alimento = max(_fecha_local(fila.fecha_hora) for fila in alimentacion)
        filas_dia = [
            fila for fila in alimentacion if _fecha_local(fila.fecha_hora) == fecha_alimento
        ]
        if all(fila.cantidad_kg is not None for fila in filas_dia):
            alimento_diario = _d3(
                sum((fila.cantidad_kg or Decimal("0")) for fila in filas_dia)
            )
            motivo_alimento = RAZON_SIN_ALIMENTO
        else:
            motivo_alimento = RAZON_ALIMENTO_UNIDAD

    evaluaciones.append(
        eval_svc.evaluar_objetivo(
            indicador="alimentacion_diaria_kg",
            etiqueta="Alimentación real del último día registrado",
            real=alimento_diario,
            objetivo=ctx.indicadores.racion_diaria_recomendada_kg,
            unidad="kg/día",
            referencia=(
                f"Ración recomendada / semana productiva {ctx.indicadores.semana_productiva_alimentacion}"
                if ctx.indicadores.racion_diaria_recomendada_kg is not None
                else None
            ),
            fecha_real=fecha_alimento,
            fecha_referencia=_hoy_bogota(),
            motivo_sin_datos=motivo_alimento,
            motivo_sin_referencia=ctx.pendientes.get(
                "racion_diaria_recomendada_kg", RAZON_SIN_REFERENCIA
            ),
        )
    )

    evaluaciones.extend(
        [
            eval_svc.evaluar_objetivo(
                indicador="fca",
                etiqueta="FCA acumulado",
                real=ctx.indicadores.fca,
                objetivo=None,
                unidad=None,
                motivo_sin_datos=ctx.indicadores.fca_motivo or FCA_SIN_BIOMASA_FINAL,
                motivo_sin_referencia="SIN_REFERENCIA_FCA",
            ),
            eval_svc.evaluar_objetivo(
                indicador="mortalidad_porcentaje",
                etiqueta="Mortalidad acumulada",
                real=ctx.indicadores.mortalidad_porcentaje,
                objetivo=None,
                unidad="%",
                motivo_sin_referencia="SIN_REFERENCIA_MORTALIDAD",
            ),
            eval_svc.evaluar_objetivo(
                indicador="supervivencia_porcentaje",
                etiqueta="Supervivencia",
                real=ctx.indicadores.supervivencia_porcentaje,
                objetivo=None,
                unidad="%",
                motivo_sin_referencia="SIN_REFERENCIA_SUPERVIVENCIA",
            ),
            _evaluar_biofloc(
                db,
                lote,
                indicador="volumen_sedimentable",
                etiqueta="Sólidos sedimentables",
                real=biofloc.volumen_sedimentable if biofloc else None,
                unidad=biofloc.unidad if biofloc else None,
                fecha_real=_fecha_local(biofloc.fecha_hora) if biofloc else None,
            ),
            _evaluar_biofloc(
                db,
                lote,
                indicador="relacion_cn",
                etiqueta="Relación C:N",
                real=biofloc.relacion_cn if biofloc else None,
                unidad=None,
                fecha_real=_fecha_local(biofloc.fecha_hora) if biofloc else None,
            ),
        ]
    )
    for evaluacion in evaluaciones:
        if evaluacion.indicador in {"volumen_sedimentable", "relacion_cn"}:
            recomendacion = eval_svc.recomendacion_agua(evaluacion)
            if recomendacion is not None:
                recomendaciones.append(recomendacion)
    return evaluaciones, recomendaciones


def _cargar_lote(db: Session, lote_id: int) -> Lote:
    lote = (
        db.query(Lote)
        .options(
            joinedload(Lote.estanque),
            joinedload(Lote.especie),
            joinedload(Lote.etapa_productiva),
            joinedload(Lote.estado),
        )
        .filter(Lote.id == lote_id)
        .first()
    )
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


def _calcular_indicadores(db: Session, lote: Lote) -> _Contexto:
    """Indicadores puntuales del lote con las fórmulas oficiales de Etapa 3."""
    sembrados = _i(lote.cantidad_sembrada)
    mort_acum, cosechados = obtener_salidas_peces(db, lote.id)
    poblacion = calcular_poblacion_disponible(sembrados, mort_acum, cosechados)
    surv = supervivencia_biologica_pct(sembrados, mort_acum)
    mort_pct = mortalidad_pct(sembrados, mort_acum)
    biomasa_cosechada_kg = _d3(
        Decimal(
            str(
                db.query(func.coalesce(func.sum(Cosecha.peso_total_kg), 0))
                .filter(Cosecha.lote_id == lote.id)
                .scalar()
                or 0
            )
        )
    )

    ultima = db.execute(
        text(SQL_ULTIMA_BIOMETRIA_LOTE),
        {"lote_id": lote.id},
    ).mappings().first()

    if ultima:
        ultima_id = _i(ultima["id"])
        talla_promedio = _d2n(ultima["talla_promedio"])
        unidad_talla = str(ultima["unidad_talla"]) if ultima["unidad_talla"] else None
        peso_promedio_g = _d3n(ultima["peso_promedio_g"])
    else:
        ultima_id = None
        talla_promedio = None
        unidad_talla = None
        peso_promedio_g = None

    dias, semana = _dias_y_semana(lote.fecha_siembra, lote.fecha_cierre)
    peso_inicial_g = _d3n(lote.peso_inicial_promedio_g)

    alim_u = db.execute(
        text(
            """
            SELECT u.simbolo AS unidad, COALESCE(SUM(a.cantidad), 0) AS cantidad
            FROM alimentaciones a
            JOIN productos p ON p.id = a.producto_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE a.lote_id = :lote_id
            GROUP BY u.simbolo
            ORDER BY u.simbolo
            """
        ),
        {"lote_id": lote.id},
    ).mappings()
    alimentacion_por_unidad = [
        AlimentoUnidadOut(unidad=str(r["unidad"]), cantidad=_d3(r["cantidad"])) for r in alim_u
    ]

    pendientes: dict[str, str] = {}

    # Histórico inválido: se reporta, no se corrige ni se oculta con MAX(0).
    if poblacion < 0:
        pendientes["poblacion_estimada"] = RAZON_POBLACION_NEGATIVA
        logger.warning(
            "Población histórica negativa lote_id=%s codigo=%s sembrados=%s "
            "mortalidad=%s cosechados=%s poblacion=%s. No se modifica el dato.",
            lote.id,
            lote.codigo,
            sembrados,
            mort_acum,
            cosechados,
            poblacion,
        )

    # Biomasa inicial: cantidad sembrada × peso inicial (g) / 1000.
    if peso_inicial_g is None:
        biomasa_inicial_kg = None
        pendientes["biomasa_inicial_kg"] = RAZON_SIN_PESO_INICIAL
    else:
        biomasa_inicial_kg = biomasa_kg(sembrados, peso_inicial_g)

    # Biomasa actual: población estimada × peso promedio (g) / 1000.
    if peso_promedio_g is None:
        biomasa_actual_kg = None
        pendientes["biomasa_actual_kg"] = RAZON_SIN_BIOMETRIA
    else:
        biomasa_actual_kg = biomasa_kg(poblacion, peso_promedio_g)

    # Ganancia de peso: peso promedio actual − peso promedio inicial.
    if peso_promedio_g is None:
        ganancia_peso_g = None
        pendientes["ganancia_peso_g"] = RAZON_SIN_BIOMETRIA
    elif peso_inicial_g is None:
        ganancia_peso_g = None
        pendientes["ganancia_peso_g"] = RAZON_SIN_PESO_INICIAL
    else:
        ganancia_peso_g = _d3(peso_promedio_g - peso_inicial_g)

    # Ganancia diaria: ganancia / días de cultivo.
    ganancia_diaria_g, motivo_gpd = gpd_oficial(ganancia_peso_g, dias)
    if ganancia_diaria_g is None:
        if ganancia_peso_g is None:
            pendientes["ganancia_diaria_g"] = pendientes.get("ganancia_peso_g", RAZON_SIN_BIOMETRIA)
        else:
            pendientes["ganancia_diaria_g"] = motivo_gpd or RAZON_DIAS_CERO

    sgr, sgr_motivo = sgr_pct_dia(peso_inicial_g, peso_promedio_g, dias)
    if sgr is None and sgr_motivo:
        pendientes["sgr_pct_dia"] = sgr_motivo

    volumen = volumen_estanque_m3(
        Decimal(str(lote.estanque.diametro)) if lote.estanque and lote.estanque.diametro is not None else None,
        Decimal(str(lote.estanque.profundidad)) if lote.estanque and lote.estanque.profundidad is not None else None,
    )
    densidad, dens_motivo = dens_oficial(biomasa_actual_kg, volumen)
    if densidad is None and dens_motivo:
        pendientes["densidad_kg_m3"] = dens_motivo

    alimento_kg, razon_alimento = _alimento_kg(alimentacion_por_unidad)
    if alimento_kg is not None:
        alimento_kg = _d3(alimento_kg)
    if alimento_kg is None and razon_alimento is not None:
        pendientes["alimento_real_acumulado_kg"] = razon_alimento

    ganancia_biomasa, motivo_ganancia = ganancia_biomasa_productiva_kg(
        biomasa_actual_kg,
        biomasa_inicial_kg,
        biomasa_cosechada_kg,
        hay_cosecha=cosechados > 0,
        cosecha_con_peso=biomasa_cosechada_kg > 0,
    )
    fca, fca_motivo = _fca_oficial(alimento_kg, razon_alimento, ganancia_biomasa, motivo_ganancia)
    if fca_motivo is not None:
        pendientes["fca"] = fca_motivo

    referencia = ref_svc.resolver_referencia_aplicable(
        db, lote.especie_id, lote.etapa_productiva_id, semana
    )

    resultado_alim = alim_ref_svc.calcular_racion_lote(
        db,
        lote,
        dias_cultivo=dias,
        peso_inicial_g=peso_inicial_g,
        peso_real_g=peso_promedio_g,
    )
    params_alim = resultado_alim.parametros
    racion_kg = resultado_alim.racion_diaria_kg
    if params_alim is not None:
        referencia_alimentacion = ReferenciaAlimentacionActivaOut(
            semana_productiva=resultado_alim.semana_productiva,
            fase=params_alim.fase,
            peso_esperado_g=params_alim.peso_esperado_g,
            peso_real_g=peso_promedio_g,
            peso_inicial_g=peso_inicial_g,
            peso_operativo_g=resultado_alim.peso_operativo_g,
            peso_para_racion_g=resultado_alim.peso_para_racion_g,
            basada_en_peso=resultado_alim.basada_en_peso,
            peso_utilizado=resultado_alim.peso_utilizado,
            diferencia_peso_g=resultado_alim.diferencia_peso_g,
            poblacion_estimada=resultado_alim.poblacion,
            biomasa_esperada_kg=resultado_alim.biomasa_esperada_kg,
            biomasa_para_racion_kg=resultado_alim.biomasa_para_racion_kg,
            tasa_alimentacion_pct=params_alim.tasa_alimentacion_pct,
            raciones_diarias=params_alim.raciones_texto,
            raciones_min=params_alim.raciones_min,
            raciones_max=params_alim.raciones_max,
            numero_raciones_diarias=params_alim.numero_raciones_diarias,
            racion_diaria_recomendada_kg=racion_kg,
            racion_diaria_recomendada_g=resultado_alim.racion_diaria_g,
            racion_por_comida_kg=resultado_alim.racion_por_comida_kg,
            racion_por_comida_g=resultado_alim.racion_por_comida_g,
            racion_por_comida_min_kg=resultado_alim.racion_por_comida_min_kg,
            racion_por_comida_max_kg=resultado_alim.racion_por_comida_max_kg,
            racion_por_comida_min_g=resultado_alim.racion_por_comida_min_g,
            racion_por_comida_max_g=resultado_alim.racion_por_comida_max_g,
            alimento_referencia_1000_peces_kg=params_alim.alimento_referencia_1000_peces_kg,
            fuente=params_alim.fuente,
            referencia_bd_id=params_alim.referencia_bd_id,
        )
    else:
        referencia_alimentacion = None
    pendientes.update(resultado_alim.pendientes)

    indicadores = IndicadoresLoteOut(
        peces_sembrados=sembrados,
        mortalidad_acumulada=mort_acum,
        peces_cosechados=cosechados,
        poblacion_estimada=poblacion,
        supervivencia_porcentaje=surv,
        mortalidad_porcentaje=mort_pct,
        ultima_biometria_id=ultima_id,
        peso_promedio_g=peso_promedio_g,
        talla_promedio=talla_promedio,
        unidad_talla=unidad_talla,
        fecha_ultima_biometria=ultima["fecha_hora"] if ultima else None,
        peso_inicial_g=peso_inicial_g,
        dias_cultivo=dias,
        semana_cultivo=semana,
        ganancia_peso_g=ganancia_peso_g,
        ganancia_diaria_g=ganancia_diaria_g,
        biomasa_inicial_kg=biomasa_inicial_kg,
        biomasa_actual_kg=biomasa_actual_kg,
        alimento_real_acumulado_kg=alimento_kg,
        fca=fca,
        fca_disponible=fca is not None,
        fca_motivo=fca_motivo,
        sgr_pct_dia=sgr,
        densidad_kg_m3=densidad,
        volumen_util_m3=volumen,
        racion_diaria_recomendada_kg=racion_kg,
        numero_raciones_diarias=params_alim.numero_raciones_diarias if params_alim else None,
        semana_productiva_alimentacion=resultado_alim.semana_productiva,
        biomasa_esperada_kg=resultado_alim.biomasa_esperada_kg,
        raciones_diarias_texto=params_alim.raciones_texto if params_alim else None,
        racion_por_comida_kg=resultado_alim.racion_por_comida_kg,
        racion_basada_en_peso=resultado_alim.basada_en_peso,
    )

    return _Contexto(
        sembrados=sembrados,
        mortalidad_acumulada=mort_acum,
        cosechados=cosechados,
        poblacion=poblacion,
        dias=dias,
        semana=semana,
        peso_inicial_g=peso_inicial_g,
        peso_promedio_g=peso_promedio_g,
        biomasa_inicial_kg=biomasa_inicial_kg,
        biomasa_actual_kg=biomasa_actual_kg,
        biomasa_cosechada_kg=biomasa_cosechada_kg,
        ganancia_biomasa_kg=ganancia_biomasa,
        alimento_por_unidad=alimentacion_por_unidad,
        alimento_kg=alimento_kg,
        razon_alimento=razon_alimento,
        referencia=referencia,
        referencia_alimentacion=referencia_alimentacion,
        indicadores=indicadores,
        pendientes=pendientes,
    )


# --- Reconstrucción histórica ----------------------------------------------


class _Acumulador:
    """Acumulado de un evento contable (mortalidad o cosecha) por fecha.

    Permite preguntar cuánto se acumuló hasta un instante, incluyendo los
    eventos que ocurren exactamente en ese instante.
    """

    def __init__(self, filas: list[tuple[datetime, int]]) -> None:
        self.fechas: list[datetime] = []
        self.acumulado: list[int] = []
        total = 0
        for fecha, cantidad in filas:
            total += cantidad
            self.fechas.append(fecha)
            self.acumulado.append(total)

    def hasta(self, momento: datetime) -> int:
        indice = bisect_right(self.fechas, momento)
        return self.acumulado[indice - 1] if indice else 0


class _AcumuladorKg:
    """Acumulado de masa (kg) por fecha, para biomasa cosechada as-of."""

    def __init__(self, filas: list[tuple[datetime, Decimal]]) -> None:
        self.fechas: list[datetime] = []
        self.acumulado: list[Decimal] = []
        total = Decimal("0")
        for fecha, cantidad in filas:
            total += cantidad
            self.fechas.append(fecha)
            self.acumulado.append(total)

    def hasta(self, momento: datetime) -> Decimal:
        indice = bisect_right(self.fechas, momento)
        return self.acumulado[indice - 1] if indice else Decimal("0")


def _poblacion_as_of(
    sembrados: int, morts: _Acumulador, cosechas: _Acumulador, momento: datetime
) -> tuple[int, int, int]:
    """Población a la fecha: sembrados − mortalidades − cosechas hasta el momento."""
    mortalidad = morts.hasta(momento)
    cosechados = cosechas.hasta(momento)
    return sembrados - mortalidad - cosechados, mortalidad, cosechados


def _momento_siembra(fecha_siembra: date) -> datetime:
    return datetime.combine(fecha_siembra, time.min, tzinfo=TZ)


def _en_rango(momento: datetime, desde: Optional[date], hasta: Optional[date]) -> bool:
    fecha = _fecha_local(momento)
    if desde is not None and fecha < desde:
        return False
    if hasta is not None and fecha > hasta:
        return False
    return True


# --- Análisis completo del lote --------------------------------------------


def analizar_lote(
    db: Session,
    lote_id: int,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> AnalisisLoteCompletoOut:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=422, detail="fecha_desde no puede ser posterior a fecha_hasta"
        )

    lote = _cargar_lote(db, lote_id)
    ctx = _calcular_indicadores(db, lote)
    pendientes = ctx.pendientes

    def visible(momento: datetime) -> bool:
        return _en_rango(momento, fecha_desde, fecha_hasta)

    # Eventos contables completos: la reconstrucción as-of siempre parte de la
    # siembra, aunque la ventana de fechas recorte lo que se devuelve.
    morts_filas = [
        (r["fecha_hora"], _i(r["cantidad"]), _i(r["id"]))
        for r in db.execute(
            text(
                """
                SELECT id, fecha_hora, cantidad
                FROM mortalidades
                WHERE lote_id = :lote_id
                ORDER BY fecha_hora ASC, id ASC
                """
            ),
            {"lote_id": lote_id},
        ).mappings()
    ]
    cosechas_filas = [
        (r["fecha_hora"], _i(r["cantidad_peces"]), _d3(r["peso_total_kg"]))
        for r in db.execute(
            text(
                """
                SELECT fecha_hora, cantidad_peces, peso_total_kg
                FROM cosechas
                WHERE lote_id = :lote_id
                ORDER BY fecha_hora ASC, id ASC
                """
            ),
            {"lote_id": lote_id},
        ).mappings()
    ]
    acum_morts = _Acumulador([(fecha, cantidad) for fecha, cantidad, _ in morts_filas])
    acum_cosechas = _Acumulador([(fecha, cantidad) for fecha, cantidad, _ in cosechas_filas])
    acum_cosecha_kg = _AcumuladorKg([(fecha, peso) for fecha, _, peso in cosechas_filas])

    bio_filas = [
        dict(r)
        for r in db.execute(
            text(
                """
                SELECT id, fecha_hora, cantidad_muestra, peso_total_muestra_g,
                       ROUND(peso_total_muestra_g / NULLIF(cantidad_muestra, 0), 3) AS peso_promedio_g,
                       talla_promedio, unidad_talla
                FROM biometrias
                WHERE lote_id = :lote_id
                ORDER BY fecha_hora ASC, id ASC
                """
            ),
            {"lote_id": lote_id},
        ).mappings()
    ]

    # Referencia de producción resuelta para cada semana del historial, nunca
    # con la referencia de la semana actual para todo el ciclo.
    semanas_bio = {
        _dias_semana(lote.fecha_siembra, _fecha_local(fila["fecha_hora"]))[1] for fila in bio_filas
    }
    semanas = sorted(semanas_bio | {ctx.semana})
    referencias_por_semana = []
    for semana in semanas:
        # La semana N se busca como N. Nunca semana → días → semana (eso desfasaba a N-1).
        params_alim = alim_ref_svc.resolver_parametros_semana(
            db, lote.especie_id, lote.etapa_productiva_id, semana
        )
        if params_alim is None:
            referencias_por_semana.append(
                ReferenciaSemanaOut(
                    semana_cultivo=semana,
                    referencia_id=None,
                    peso_esperado_g=None,
                    tasa_alimentacion_pct=None,
                    motivo="SIN_REFERENCIA_PRODUCCION_APLICABLE",
                )
            )
            continue
        referencias_por_semana.append(
            ReferenciaSemanaOut(
                semana_cultivo=semana,
                referencia_id=params_alim.referencia_bd_id,
                peso_esperado_g=_d2n(params_alim.peso_esperado_g),
                tasa_alimentacion_pct=params_alim.tasa_alimentacion_pct,
                motivo=None,
            )
        )

    ref_por_semana = {item.semana_cultivo: item for item in referencias_por_semana}

    # Serie de peso: real de la biometría contra el esperado de su propia semana.
    biometrias: list[BiometriaSerieOut] = []
    for fila in bio_filas:
        _, semana_punto = _dias_semana(lote.fecha_siembra, _fecha_local(fila["fecha_hora"]))
        ref_row = ref_por_semana.get(semana_punto)
        esperado = _d2n(ref_row.peso_esperado_g) if ref_row else None
        peso = _d3n(fila["peso_promedio_g"])
        diferencia = None
        diferencia_pct = None
        if peso is not None and esperado is not None:
            diferencia = _d3(peso - esperado)
            if esperado != 0:
                diferencia_pct = ((peso - esperado) / esperado * CIEN).quantize(
                    D2, rounding=ROUND_HALF_UP
                )
        biometrias.append(
            BiometriaSerieOut(
                id=_i(fila["id"]),
                fecha_hora=fila["fecha_hora"],
                cantidad_muestra=_i(fila["cantidad_muestra"]),
                peso_total_muestra_g=_d3(fila["peso_total_muestra_g"]),
                peso_promedio_g=peso,
                talla_promedio=_d2n(fila["talla_promedio"]),
                unidad_talla=str(fila["unidad_talla"]) if fila["unidad_talla"] else None,
                semana_cultivo=semana_punto,
                referencia_id=ref_row.referencia_id if ref_row else None,
                peso_esperado_g=esperado,
                diferencia_peso_g=diferencia,
                diferencia_peso_pct=diferencia_pct,
            )
        )

    # Serie de mortalidad con acumulado y porcentaje sobre lo sembrado.
    mortalidades: list[MortalidadSerieOut] = []
    acumulado_mort = 0
    for fecha, cantidad, ident in morts_filas:
        acumulado_mort += cantidad
        mortalidades.append(
            MortalidadSerieOut(
                id=ident,
                fecha_hora=fecha,
                cantidad=cantidad,
                acumulada=acumulado_mort,
                mortalidad_porcentaje=_porcentaje(acumulado_mort, ctx.sembrados),
            )
        )

    # Serie de población y supervivencia: un punto por evento productivo.
    eventos: dict[datetime, set[str]] = {}
    momento_siembra = _momento_siembra(lote.fecha_siembra)
    eventos.setdefault(momento_siembra, set()).add("SIEMBRA")
    for fecha, _cantidad, _ident in morts_filas:
        eventos.setdefault(fecha, set()).add("MORTALIDAD")
    for fecha, _cantidad, _peso in cosechas_filas:
        eventos.setdefault(fecha, set()).add("COSECHA")
    for fila in bio_filas:
        eventos.setdefault(fila["fecha_hora"], set()).add("BIOMETRIA")

    serie_poblacion: list[PoblacionPuntoOut] = []
    for momento in sorted(eventos):
        poblacion_punto, mortalidad_punto, cosechados_punto = _poblacion_as_of(
            ctx.sembrados, acum_morts, acum_cosechas, momento
        )
        serie_poblacion.append(
            PoblacionPuntoOut(
                fecha_hora=momento,
                evento="+".join(sorted(eventos[momento])),
                mortalidad_acumulada=mortalidad_punto,
                peces_cosechados=cosechados_punto,
                poblacion_estimada=poblacion_punto,
                mortalidad_porcentaje=_porcentaje(mortalidad_punto, ctx.sembrados),
                supervivencia_porcentaje=supervivencia_biologica_pct(
                    ctx.sembrados, mortalidad_punto
                ),
            )
        )

    # Alimentación real: producto, unidad original, kg cuando es convertible y
    # acumulado que respeta la regla del indicador.
    alim_filas = db.execute(
        text(
            """
            SELECT a.id, a.fecha_hora, a.producto_id, p.codigo AS producto_codigo,
                   p.nombre AS producto_nombre, u.simbolo AS unidad, a.cantidad
            FROM alimentaciones a
            JOIN productos p ON p.id = a.producto_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE a.lote_id = :lote_id
            ORDER BY a.fecha_hora ASC, a.id ASC
            """
        ),
        {"lote_id": lote_id},
    ).mappings()

    alimentacion_real: list[AlimentoRegistroOut] = []
    alim_fechas: list[datetime] = []
    alim_acumulado: list[Optional[Decimal]] = []
    acumulado_kg = Decimal("0")
    hay_incompatible = False
    for fila in alim_filas:
        factor = FACTOR_A_KG.get(str(fila["unidad"]))
        cantidad = _d3(fila["cantidad"])
        if factor is None:
            hay_incompatible = True
            cantidad_kg = None
        else:
            cantidad_kg = _d3(cantidad * factor)
            acumulado_kg += cantidad_kg
        acumulado_visible = None if hay_incompatible else _d3(acumulado_kg)
        alimentacion_real.append(
            AlimentoRegistroOut(
                id=_i(fila["id"]),
                fecha_hora=fila["fecha_hora"],
                producto_id=_i(fila["producto_id"]),
                producto_codigo=str(fila["producto_codigo"]),
                producto_nombre=str(fila["producto_nombre"]),
                unidad=str(fila["unidad"]),
                cantidad=cantidad,
                cantidad_kg=cantidad_kg,
                acumulado_kg=acumulado_visible,
                convertible_a_kg=factor is not None,
            )
        )
        alim_fechas.append(fila["fecha_hora"])
        alim_acumulado.append(acumulado_visible)

    def alimento_hasta(momento: datetime) -> tuple[Optional[Decimal], Optional[str]]:
        indice = bisect_right(alim_fechas, momento)
        if indice == 0:
            return None, RAZON_SIN_ALIMENTO
        valor = alim_acumulado[indice - 1]
        if valor is None:
            return None, RAZON_ALIMENTO_UNIDAD
        return valor, None

    # Series de biomasa y FCA: un punto por biometría, con población as-of.
    serie_biomasa: list[BiomasaPuntoOut] = []
    serie_crecimiento: list[CrecimientoPuntoOut] = []
    serie_fca: list[FcaPuntoOut] = []
    for fila in bio_filas:
        peso = _d3n(fila["peso_promedio_g"])
        if peso is None:
            continue
        momento = fila["fecha_hora"]
        dias_punto, _ = _dias_semana(lote.fecha_siembra, _fecha_local(momento))
        ganancia_peso = (
            None if ctx.peso_inicial_g is None else _d3(peso - ctx.peso_inicial_g)
        )
        ganancia_diaria, motivo_gpd = gpd_oficial(ganancia_peso, dias_punto)
        if ganancia_peso is None:
            motivo_crecimiento = "SIN_PESO_INICIAL"
        else:
            motivo_crecimiento = motivo_gpd
        serie_crecimiento.append(
            CrecimientoPuntoOut(
                fecha_hora=momento,
                biometria_id=_i(fila["id"]),
                dias_cultivo=dias_punto,
                peso_promedio_g=peso,
                ganancia_peso_g=ganancia_peso,
                ganancia_diaria_g=ganancia_diaria,
                motivo=motivo_crecimiento,
            )
        )
        poblacion_punto, _m, cosechados_punto = _poblacion_as_of(
            ctx.sembrados, acum_morts, acum_cosechas, momento
        )
        biomasa_punto = biomasa_kg(poblacion_punto, peso)
        cosechada_punto = acum_cosecha_kg.hasta(momento)
        ganancia, motivo_ganancia = ganancia_biomasa_productiva_kg(
            biomasa_punto,
            ctx.biomasa_inicial_kg,
            cosechada_punto,
            hay_cosecha=cosechados_punto > 0,
            cosecha_con_peso=cosechada_punto > 0,
        )
        serie_biomasa.append(
            BiomasaPuntoOut(
                fecha_hora=momento,
                biometria_id=_i(fila["id"]),
                poblacion_estimada=poblacion_punto,
                peso_promedio_g=peso,
                biomasa_kg=biomasa_punto,
                ganancia_biomasa_kg=ganancia,
            )
        )

        alimento_punto, razon_punto = alimento_hasta(momento)
        fca_punto, motivo_punto = _fca_oficial(
            alimento_punto, razon_punto, ganancia, motivo_ganancia
        )
        serie_fca.append(
            FcaPuntoOut(
                fecha_hora=momento,
                biometria_id=_i(fila["id"]),
                alimento_real_acumulado_kg=alimento_punto,
                biomasa_kg=biomasa_punto,
                ganancia_biomasa_kg=ganancia,
                fca=fca_punto,
                fca_disponible=fca_punto is not None,
                fca_motivo=motivo_punto,
            )
        )

    # Mediciones de agua con el rango de referencia de la especie y etapa del
    # lote. Sin referencia, fuera_de_rango queda en null: no se inventa objetivo.
    sql_agua = """
        SELECT {distinct}
               mw.id, pa.id AS parametro_id, pa.nombre AS parametro, pa.unidad,
               mw.valor, mw.fecha_hora, mw.registrado_por,
               u.nombre AS registrado_por_nombre,
               r.valor_minimo, r.valor_maximo,
               CASE
                 WHEN r.id IS NULL THEN NULL
                 WHEN r.valor_minimo IS NOT NULL AND mw.valor < r.valor_minimo THEN TRUE
                 WHEN r.valor_maximo IS NOT NULL AND mw.valor > r.valor_maximo THEN TRUE
                 ELSE FALSE
               END AS fuera_de_rango
        FROM mediciones_agua mw
        JOIN parametros_agua pa ON pa.id = mw.parametro_id
        LEFT JOIN usuarios u ON u.id = mw.registrado_por
        LEFT JOIN referencias_agua r
          ON r.especie_id = :especie_id
         AND r.etapa_productiva_id = :etapa_id
         AND r.parametro_id = mw.parametro_id
         AND r.activo = TRUE
        WHERE mw.lote_id = :lote_id
        ORDER BY {orden}
    """
    params_agua = {
        "lote_id": lote_id,
        "especie_id": lote.especie_id,
        "etapa_id": lote.etapa_productiva_id,
    }

    def _agua(row) -> AguaMedicionOut:
        return AguaMedicionOut(
            id=_i(row["id"]),
            parametro_id=_i(row["parametro_id"]),
            parametro=str(row["parametro"]),
            unidad=str(row["unidad"]),
            valor=_d4n(row["valor"]) or Decimal("0.0000"),
            fecha_hora=row["fecha_hora"],
            valor_minimo=_d4n(row["valor_minimo"]),
            valor_maximo=_d4n(row["valor_maximo"]),
            fuera_de_rango=row["fuera_de_rango"],
            registrado_por=_i(row["registrado_por"]) if row.get("registrado_por") is not None else None,
            registrado_por_nombre=(
                str(row["registrado_por_nombre"]) if row.get("registrado_por_nombre") else None
            ),
        )

    agua = [
        _agua(r)
        for r in db.execute(
            text(
                sql_agua.format(
                    distinct="DISTINCT ON (mw.parametro_id)",
                    orden="mw.parametro_id, mw.fecha_hora DESC, mw.id DESC",
                )
            ),
            params_agua,
        ).mappings()
    ]
    agua_serie = [
        _agua(r)
        for r in db.execute(
            text(sql_agua.format(distinct="", orden="mw.fecha_hora ASC, mw.id ASC")),
            params_agua,
        ).mappings()
    ]

    bio_rows = db.execute(
        text(
            """
            SELECT mb.id, mb.fecha_hora, mb.volumen_sedimentable, mb.unidad, mb.relacion_cn,
                   mb.registrado_por, u.nombre AS registrado_por_nombre
            FROM mediciones_biofloc mb
            LEFT JOIN usuarios u ON u.id = mb.registrado_por
            WHERE mb.lote_id = :lote_id
            ORDER BY mb.fecha_hora ASC, mb.id ASC
            """
        ),
        {"lote_id": lote_id},
    ).mappings()
    biofloc_serie = [
        BioflocMedicionOut(
            id=_i(r["id"]),
            fecha_hora=r["fecha_hora"],
            volumen_sedimentable=_d2(r["volumen_sedimentable"]),
            unidad=str(r["unidad"]),
            relacion_cn=_d3n(r["relacion_cn"]),
            registrado_por=_i(r["registrado_por"]) if r.get("registrado_por") is not None else None,
            registrado_por_nombre=(
                str(r["registrado_por_nombre"]) if r.get("registrado_por_nombre") else None
            ),
        )
        for r in bio_rows
    ]
    biofloc = biofloc_serie[-1] if biofloc_serie else None

    # Ventana de fechas: recorta lo que se devuelve, no lo que se calcula.
    alimentacion_real_completa = list(alimentacion_real)

    from collections import defaultdict

    alim_por_dia: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for reg in alimentacion_real_completa:
        if reg.cantidad_kg is not None:
            alim_por_dia[_fecha_local(reg.fecha_hora)] += reg.cantidad_kg
    bio_fechas_alim: list[datetime] = []
    bio_pesos_alim: list[Decimal] = []
    for fila in bio_filas:
        peso_bio = _d3n(fila["peso_promedio_g"])
        if peso_bio is not None:
            bio_fechas_alim.append(fila["fecha_hora"])
            bio_pesos_alim.append(peso_bio)
    serie_alim_raw = alim_ref_svc.construir_serie_alimentacion_comparativa(
        db,
        lote,
        sembrados=ctx.sembrados,
        acum_morts=acum_morts,
        acum_cosechas=acum_cosechas,
        bio_fechas=bio_fechas_alim,
        bio_pesos=bio_pesos_alim,
        alimentacion_por_dia=dict(alim_por_dia),
    )
    serie_alimentacion_comparativa = [
        AlimentacionComparativaPuntoOut(
            fecha=p["fecha"].isoformat(),
            real_kg=p["real_kg"],
            recomendada_kg=p["recomendada_kg"],
            desviacion_kg=p["desviacion_kg"],
            desviacion_porcentaje=p["desviacion_porcentaje"],
            semana_cultivo=p["semana_cultivo"],
        )
        for p in serie_alim_raw
        if _en_rango(datetime.combine(p["fecha"], time.min, tzinfo=TZ), fecha_desde, fecha_hasta)
    ]

    biometrias = [p for p in biometrias if visible(p.fecha_hora)]
    mortalidades = [p for p in mortalidades if visible(p.fecha_hora)]
    serie_poblacion = [p for p in serie_poblacion if visible(p.fecha_hora)]
    serie_biomasa = [p for p in serie_biomasa if visible(p.fecha_hora)]
    serie_crecimiento = [p for p in serie_crecimiento if visible(p.fecha_hora)]
    serie_fca = [p for p in serie_fca if visible(p.fecha_hora)]
    agua_serie = [p for p in agua_serie if visible(p.fecha_hora)]
    biofloc_serie_visible = [p for p in biofloc_serie if visible(p.fecha_hora)]
    alimentacion_real = [p for p in alimentacion_real if visible(p.fecha_hora)]

    estadisticas = EstadisticasAnalisisOut(
        peso_promedio_g=est_svc.stats_serie([p.peso_promedio_g for p in biometrias], "g"),
        talla_promedio=_stats_talla(biometrias),
        biomasa_kg=est_svc.stats_serie([p.biomasa_kg for p in serie_biomasa], "kg"),
        poblacion_estimada=est_svc.stats_serie(
            [Decimal(p.poblacion_estimada) for p in serie_poblacion], "peces"
        ),
        supervivencia_porcentaje=est_svc.stats_serie(
            [p.supervivencia_porcentaje for p in serie_poblacion], "%"
        ),
        mortalidad_acumulada=est_svc.stats_serie(
            [Decimal(p.acumulada) for p in mortalidades], "peces"
        ),
        alimento_acumulado_kg=est_svc.stats_serie(
            [p.acumulado_kg for p in alimentacion_real], "kg"
        ),
        fca=est_svc.stats_serie([p.fca for p in serie_fca], None),
        volumen_sedimentable=est_svc.stats_serie(
            [p.volumen_sedimentable for p in biofloc_serie_visible],
            biofloc_serie_visible[-1].unidad if biofloc_serie_visible else None,
        ),
        relacion_cn=est_svc.stats_serie([p.relacion_cn for p in biofloc_serie_visible], None),
        agua=_estadisticas_agua(agua_serie),
    )

    comparaciones = ComparacionesAnalisisOut(
        peso_g=_comparacion(
            real=ctx.peso_promedio_g,
            objetivo=(
                _d2n(ctx.referencia_alimentacion.peso_esperado_g)
                if ctx.referencia_alimentacion is not None
                else None
            ),
            unidad="g",
            motivo_sin_real=RAZON_SIN_BIOMETRIA,
            motivo_sin_objetivo=(
                RAZON_SIN_REFERENCIA
                if ctx.referencia_alimentacion is None
                else RAZON_SIN_PESO_ESPERADO
            ),
        )
    )
    evaluaciones, recomendaciones = _construir_evaluaciones(
        db=db,
        lote=lote,
        ctx=ctx,
        agua=agua,
        biofloc=biofloc,
        alimentacion=alimentacion_real_completa,
    )
    productividad, eficiencia, finanzas = _bloques_productivos(db, lote, ctx)

    return AnalisisLoteCompletoOut(
        lote=AnalisisLoteOut(
            id=lote.id,
            codigo=lote.codigo,
            fecha_siembra=lote.fecha_siembra,
            fecha_cierre=lote.fecha_cierre,
            cantidad_sembrada=lote.cantidad_sembrada,
            peso_inicial_promedio_g=ctx.peso_inicial_g,
            estado=EstadoLoteOut.model_validate(lote.estado),
        ),
        estanque=AnalisisEstanqueOut(
            id=lote.estanque.id,
            codigo=lote.estanque.codigo,
            nombre=lote.estanque.nombre,
        ),
        especie=EspecieOut.model_validate(lote.especie),
        etapa=EtapaProductivaOut.model_validate(lote.etapa_productiva),
        definiciones=DEFINICIONES,
        filtros=FiltrosAnalisisOut(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            nota=DEFINICIONES.filtros_fecha,
        ),
        indicadores=ctx.indicadores,
        pendientes=pendientes,
        referencia_produccion=(
            ReferenciaProduccionOut.model_validate(ctx.referencia)
            if ctx.referencia is not None
            else None
        ),
        referencias_por_semana=referencias_por_semana,
        comparaciones=comparaciones,
        evaluaciones=evaluaciones,
        recomendaciones=recomendaciones,
        productividad=productividad,
        eficiencia=eficiencia,
        finanzas=finanzas,
        estadisticas=estadisticas,
        biometrias=biometrias,
        mortalidades=mortalidades,
        serie_poblacion=serie_poblacion,
        serie_biomasa=serie_biomasa,
        serie_crecimiento=serie_crecimiento,
        serie_fca=serie_fca,
        agua=agua,
        agua_serie=agua_serie,
        biofloc=biofloc,
        biofloc_serie=biofloc_serie_visible,
        alimentacion_real_por_unidad=ctx.alimento_por_unidad,
        alimentacion_real=alimentacion_real,
        referencia_alimentacion=ctx.referencia_alimentacion,
        serie_alimentacion_comparativa=serie_alimentacion_comparativa,
    )


def _stats_talla(biometrias: list[BiometriaSerieOut]) -> StatsSerieOut:
    """Estadística de talla solo si todas las mediciones comparten unidad. No convierte."""
    puntos = [
        (fila.talla_promedio, fila.unidad_talla)
        for fila in biometrias
        if fila.talla_promedio is not None
    ]
    if not puntos:
        return est_svc.stats_serie([], None)
    unidades = {unidad for _, unidad in puntos}
    if len(unidades) > 1:
        return est_svc.stats_serie([], None)
    unidad = next(iter(unidades))
    return est_svc.stats_serie([valor for valor, _ in puntos], unidad)


def _estadisticas_agua(serie: list[AguaMedicionOut]) -> list[AguaParametroEstadisticasOut]:
    """Descriptivos por parámetro de agua, con conteo de mediciones fuera de rango."""
    grupos: dict[int, list[AguaMedicionOut]] = {}
    for medicion in serie:
        grupos.setdefault(medicion.parametro_id, []).append(medicion)

    salida: list[AguaParametroEstadisticasOut] = []
    for parametro_id in sorted(grupos):
        filas = grupos[parametro_id]
        ultima = filas[-1]
        con_referencia = any(fila.fuera_de_rango is not None for fila in filas)
        evaluadas = [fila for fila in filas if fila.fuera_de_rango is not None]
        fuera = sum(1 for fila in evaluadas if fila.fuera_de_rango)
        salida.append(
            AguaParametroEstadisticasOut(
                parametro_id=parametro_id,
                parametro=ultima.parametro,
                unidad=ultima.unidad,
                valor_minimo=ultima.valor_minimo,
                valor_maximo=ultima.valor_maximo,
                con_referencia=con_referencia,
                fuera_de_rango_n=fuera if con_referencia else None,
                fuera_de_rango_porcentaje=(
                    _porcentaje(fuera, len(evaluadas)) if con_referencia else None
                ),
                estadisticas=est_svc.stats_serie([fila.valor for fila in filas], ultima.unidad),
            )
        )
    return salida


# --- Comparativo por estanque ---------------------------------------------


def comparativo_estanques(
    db: Session,
    solo_activos: bool = True,
    estanque_id: Optional[int] = None,
    incluir_historial: bool = False,
) -> ComparativoEstanquesOut:
    """Un renglón por estanque con los indicadores de su lote ACTIVO.

    Reutiliza el mismo cálculo de indicadores del análisis por lote: aquí no se
    reimplementa ninguna fórmula.
    """
    estanques = db.execute(
        text(
            """
            SELECT id, codigo, nombre, activo
            FROM estanques
            WHERE (:solo_activos = FALSE OR activo = TRUE)
              AND (:estanque_id IS NULL OR id = :estanque_id)
            ORDER BY codigo ASC
            """
        ),
        {"solo_activos": solo_activos, "estanque_id": estanque_id},
    ).mappings().all()

    # El DDL admite un solo lote ACTIVO por estanque; si hubiera más, se toma el
    # de siembra más reciente.
    lotes_activos: dict[int, int] = {}
    for fila in db.execute(
        text(
            """
            SELECT l.id, l.estanque_id
            FROM lotes l
            JOIN estados_lote el ON el.id = l.estado_id
            WHERE el.nombre = 'ACTIVO'
              AND (:estanque_id IS NULL OR l.estanque_id = :estanque_id)
            ORDER BY l.fecha_siembra ASC, l.id ASC
            """
        ),
        {"estanque_id": estanque_id},
    ).mappings():
        lotes_activos[_i(fila["estanque_id"])] = _i(fila["id"])

    agua_por_lote = {
        _i(r["lote_id"]): (
            _i(r["parametros"]),
            _i(r["con_referencia"]),
            _i(r["fuera"]),
        )
        for r in db.execute(
            text(
                """
                WITH ultimas AS (
                    SELECT DISTINCT ON (mw.lote_id, mw.parametro_id)
                           mw.lote_id, mw.parametro_id, mw.valor,
                           r.id AS referencia_id, r.valor_minimo, r.valor_maximo
                    FROM mediciones_agua mw
                    JOIN lotes l ON l.id = mw.lote_id
                    LEFT JOIN referencias_agua r
                      ON r.especie_id = l.especie_id
                     AND r.etapa_productiva_id = l.etapa_productiva_id
                     AND r.parametro_id = mw.parametro_id
                     AND r.activo = TRUE
                    ORDER BY mw.lote_id, mw.parametro_id, mw.fecha_hora DESC, mw.id DESC
                )
                SELECT lote_id,
                       COUNT(*) AS parametros,
                       COUNT(referencia_id) AS con_referencia,
                       COUNT(*) FILTER (
                           WHERE referencia_id IS NOT NULL
                             AND (
                                 (valor_minimo IS NOT NULL AND valor < valor_minimo)
                                 OR (valor_maximo IS NOT NULL AND valor > valor_maximo)
                             )
                       ) AS fuera
                FROM ultimas
                GROUP BY lote_id
                """
            )
        ).mappings()
    }
    lotes_con_biofloc = {
        _i(r["lote_id"])
        for r in db.execute(
            text(
                """
                SELECT DISTINCT mb.lote_id
                FROM mediciones_biofloc mb
                WHERE (:estanque_id IS NULL OR EXISTS (
                    SELECT 1 FROM lotes l
                    WHERE l.id = mb.lote_id AND l.estanque_id = :estanque_id
                ))
                """
            ),
            {"estanque_id": estanque_id},
        ).mappings()
    }

    filas: list[EstanqueComparativoOut] = []
    total_sembrados = 0
    total_poblacion = 0
    total_mortalidad = 0
    total_biomasa = Decimal("0")
    lotes_sin_biomasa = 0
    lotes_con_fca = 0
    lotes_sin_alimento = 0
    total_alimento = Decimal("0")
    con_lote_activo = 0
    peso_cosechado = Decimal("0")
    peces_cosechados = 0
    ingresos_lotes = Decimal("0")
    gastos_lotes = Decimal("0")

    for estanque in estanques:
        estanque_id = _i(estanque["id"])
        lote_id = lotes_activos.get(estanque_id)
        if lote_id is None:
            filas.append(
                EstanqueComparativoOut(
                    estanque_id=estanque_id,
                    codigo=str(estanque["codigo"]),
                    nombre=str(estanque["nombre"]),
                    activo=bool(estanque["activo"]),
                    sin_lote_activo_motivo=RAZON_SIN_LOTE_ACTIVO,
                )
            )
            continue

        con_lote_activo += 1
        lote = _cargar_lote(db, lote_id)
        ctx = _calcular_indicadores(db, lote)
        ind = ctx.indicadores
        productividad, eficiencia, finanzas = _bloques_productivos(db, lote, ctx)
        parametros, con_referencia, fuera = agua_por_lote.get(lote_id, (0, 0, 0))

        total_sembrados += ind.peces_sembrados
        total_poblacion += ind.poblacion_estimada
        total_mortalidad += ind.mortalidad_acumulada
        if ind.biomasa_actual_kg is None:
            lotes_sin_biomasa += 1
        else:
            total_biomasa += ind.biomasa_actual_kg
        if ind.fca_disponible:
            lotes_con_fca += 1
        if ind.alimento_real_acumulado_kg is None:
            lotes_sin_alimento += 1
        else:
            total_alimento += ind.alimento_real_acumulado_kg
        peso_cosechado += productividad.peso_cosechado_kg
        peces_cosechados += productividad.peces_cosechados
        ingresos_lotes += finanzas.ingresos_lote
        gastos_lotes += finanzas.gastos_directos_lote

        filas.append(
            EstanqueComparativoOut(
                estanque_id=estanque_id,
                codigo=str(estanque["codigo"]),
                nombre=str(estanque["nombre"]),
                activo=bool(estanque["activo"]),
                lote_id=lote.id,
                lote_codigo=lote.codigo,
                especie=lote.especie.nombre_comun,
                etapa=lote.etapa_productiva.nombre,
                fecha_siembra=lote.fecha_siembra,
                dias_cultivo=ind.dias_cultivo,
                semana_cultivo=ind.semana_cultivo,
                peces_sembrados=ind.peces_sembrados,
                poblacion_estimada=ind.poblacion_estimada,
                peso_promedio_g=ind.peso_promedio_g,
                biomasa_actual_kg=ind.biomasa_actual_kg,
                supervivencia_porcentaje=ind.supervivencia_porcentaje,
                mortalidad_porcentaje=ind.mortalidad_porcentaje,
                fca=ind.fca,
                fca_disponible=ind.fca_disponible,
                fca_motivo=ind.fca_motivo,
                agua_parametros_medidos=parametros,
                agua_parametros_con_referencia=con_referencia,
                agua_parametros_fuera_de_rango=fuera if con_referencia > 0 else None,
                ganancia_peso_g=ind.ganancia_peso_g,
                alimento_real_acumulado_kg=ind.alimento_real_acumulado_kg,
                productividad=productividad,
                eficiencia=eficiencia,
                finanzas=finanzas,
                estado_biofloc=(
                    EstadoAnalitico.SIN_REFERENCIA
                    if lote_id in lotes_con_biofloc
                    else EstadoAnalitico.SIN_DATOS
                ),
            )
        )

    resumen = ResumenGranjaOut(
        estanques=len(estanques),
        estanques_con_lote_activo=con_lote_activo,
        peces_sembrados=total_sembrados,
        poblacion_estimada=total_poblacion,
        mortalidad_acumulada=total_mortalidad,
        biomasa_actual_kg=(
            _d3(total_biomasa) if con_lote_activo > lotes_sin_biomasa else None
        ),
        lotes_sin_biomasa=lotes_sin_biomasa,
        supervivencia_porcentaje=supervivencia_biologica_pct(
            total_sembrados, total_mortalidad
        ),
        mortalidad_porcentaje=_porcentaje(total_mortalidad, total_sembrados),
        lotes_con_fca=lotes_con_fca,
        fca=None,
        fca_motivo=RAZON_FCA_GRANJA,
        alimento_real_acumulado_kg=(
            _d3(total_alimento) if con_lote_activo > lotes_sin_alimento else None
        ),
        lotes_sin_alimento=lotes_sin_alimento,
        peso_cosechado_kg=_d3(peso_cosechado),
        peces_cosechados=peces_cosechados,
        ingresos_lotes_activos=ingresos_lotes.quantize(D2),
        gastos_directos_lotes_activos=gastos_lotes.quantize(D2),
        utilidad=None,
        utilidad_motivo=RAZON_UTILIDAD,
    )

    ciclos: list[CicloComparativoOut] = []
    if incluir_historial:
        ciclos_ids = db.execute(
            text(
                """
                SELECT l.id
                FROM lotes l
                WHERE (:estanque_id IS NULL OR l.estanque_id = :estanque_id)
                ORDER BY l.fecha_siembra DESC, l.id DESC
                """
            ),
            {"estanque_id": estanque_id},
        ).scalars().all()
        for ciclo_id in ciclos_ids:
            lote = _cargar_lote(db, _i(ciclo_id))
            ctx = _calcular_indicadores(db, lote)
            productividad, eficiencia, finanzas = _bloques_productivos(db, lote, ctx)
            ciclos.append(
                CicloComparativoOut(
                    lote_id=lote.id,
                    lote_codigo=lote.codigo,
                    estanque_id=lote.estanque.id,
                    estanque_codigo=lote.estanque.codigo,
                    especie=lote.especie.nombre_comun,
                    etapa=lote.etapa_productiva.nombre,
                    estado_lote=lote.estado.nombre,
                    fecha_siembra=lote.fecha_siembra,
                    fecha_cierre=lote.fecha_cierre,
                    dias_cultivo=ctx.indicadores.dias_cultivo,
                    semana_cultivo=ctx.indicadores.semana_cultivo,
                    productividad=productividad,
                    eficiencia=eficiencia,
                    finanzas=finanzas,
                )
            )

    return ComparativoEstanquesOut(
        definiciones=DEFINICIONES_COMPARATIVO,
        resumen=resumen,
        estanques=filas,
        ciclos=ciclos,
    )
