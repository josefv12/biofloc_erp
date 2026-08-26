"""Cálculo de ración recomendada y resolución oficial de referencias de producción."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from unicodedata import category, normalize
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config.referencia_alimentacion_tilapia import (
    BASE_PECES_REFERENCIA,
    ESPECIE_REFERENCIA,
    FilaReferenciaAlimentacion,
    TABLA_ALIMENTACION_TILAPIA,
    semana_productiva_alimentacion,
)
from app.models.lote import Especie, Lote
from app.models.referencia_produccion import ReferenciaProduccion
from app.services import referencia_produccion_service as ref_svc
from app.services.indicadores_lote import biomasa_kg
from app.services.poblacion_lote import obtener_poblacion_disponible

TZ = ZoneInfo("America/Bogota")
D4 = Decimal("0.0001")
D3 = Decimal("0.001")
D2 = Decimal("0.01")
D1 = Decimal("0.1")
CIEN = Decimal("100")
MIL = Decimal("1000")

BASADA_EN_PESO_REAL = "PESO_REAL"
BASADA_EN_PESO_INICIAL = "PESO_INICIAL"
PESO_UTILIZADO_REAL = "real"
PESO_UTILIZADO_INICIAL = "inicial"
FUENTE_BD = "REFERENCIA_PRODUCCION_BD"
MOTIVO_SIN_REFERENCIA = "SIN_REFERENCIA_PRODUCCION_APLICABLE"
MOTIVO_SIN_TASA = "REFERENCIA_SIN_TASA_ALIMENTACION"
MOTIVO_SIN_RACIONES = "SIN_CONFIGURACION_DE_RACIONES"
MOTIVO_SIN_PESO_OPERATIVO = "SIN_PESO_OPERATIVO"


@dataclass
class ParametrosReferenciaSemana:
    semana: int
    fase: Optional[str]
    peso_esperado_g: Optional[Decimal]
    tasa_alimentacion_pct: Optional[Decimal]
    raciones_texto: Optional[str]
    raciones_min: Optional[int]
    raciones_max: Optional[int]
    numero_raciones_diarias: Optional[int]
    alimento_referencia_1000_peces_kg: Optional[Decimal]
    referencia_bd_id: Optional[int] = None
    fuente: str = FUENTE_BD


@dataclass
class ResultadoRacionLote:
    semana_productiva: int
    parametros: Optional[ParametrosReferenciaSemana]
    peso_inicial_g: Optional[Decimal]
    peso_real_g: Optional[Decimal]
    peso_operativo_g: Optional[Decimal]
    peso_para_racion_g: Optional[Decimal]
    basada_en_peso: Optional[str]
    peso_utilizado: Optional[str]
    diferencia_peso_g: Optional[Decimal]
    poblacion: int
    biomasa_esperada_kg: Optional[Decimal]
    biomasa_para_racion_kg: Optional[Decimal]
    racion_diaria_kg: Optional[Decimal]
    racion_diaria_g: Optional[Decimal]
    racion_por_comida_kg: Optional[Decimal]
    racion_por_comida_g: Optional[Decimal]
    racion_por_comida_min_kg: Optional[Decimal]
    racion_por_comida_max_kg: Optional[Decimal]
    racion_por_comida_min_g: Optional[Decimal]
    racion_por_comida_max_g: Optional[Decimal]
    pendientes: dict[str, str]


def _d4(value: Decimal) -> Decimal:
    return value.quantize(D4, rounding=ROUND_HALF_UP)


def _d3(value: Decimal) -> Decimal:
    return value.quantize(D3, rounding=ROUND_HALF_UP)


def _d2(value: Decimal) -> Decimal:
    return value.quantize(D2, rounding=ROUND_HALF_UP)


def _d1(value: Decimal) -> Decimal:
    return value.quantize(D1, rounding=ROUND_HALF_UP)


def calcular_biomasa_kg(poblacion: int, peso_g: Decimal) -> Decimal:
    """población × peso_g / 1000. Delega a la fórmula oficial de indicadores."""
    return biomasa_kg(poblacion, peso_g)


def calcular_racion_kg(biomasa_kg: Decimal, tasa_pct: Decimal) -> Decimal:
    """Catálogo (1000 peces): 3 decimales. La ración del lote usa calcular_racion_operativa."""
    return _d3(biomasa_kg * tasa_pct / CIEN)


def peso_operativo_lote(
    peso_inicial_g: Optional[Decimal],
    peso_real_g: Optional[Decimal],
) -> Optional[Decimal]:
    """Peso operativo: última biometría; si no hay, peso inicial de siembra.

    El peso esperado de la tabla nunca entra aquí.
    """
    if peso_real_g is not None:
        return peso_real_g
    if peso_inicial_g is not None:
        return peso_inicial_g
    return None


def calcular_racion_operativa(biomasa_kg: Decimal, tasa_pct: Decimal) -> tuple[Decimal, Decimal]:
    """kg (4 dec) y g (1 dec) = biomasa × tasa / 100. Conserva 0,3479 kg / 347,9 g."""
    exacto = biomasa_kg * tasa_pct / CIEN
    return _d4(exacto), _d1(exacto * MIL)


def calcular_alimento_por_racion(
    racion_kg: Decimal,
    racion_g: Decimal,
    r_min: Optional[int],
    r_max: Optional[int],
) -> tuple[
    Optional[Decimal],
    Optional[Decimal],
    Optional[Decimal],
    Optional[Decimal],
    Optional[Decimal],
    Optional[Decimal],
]:
    """exact_kg, exact_g, min_kg, max_kg, min_g, max_g. Nunca promedia un rango."""
    if r_min is None or r_max is None:
        return None, None, None, None, None, None
    if r_min == r_max:
        n = Decimal(r_min)
        return _d3(racion_kg / n), _d1(racion_g / n), None, None, None, None
    return (
        None,
        None,
        _d4(racion_kg / Decimal(r_max)),
        _d4(racion_kg / Decimal(r_min)),
        _d2(racion_g / Decimal(r_max)),
        _d2(racion_g / Decimal(r_min)),
    )


def _resultado_sin_calculo(
    *,
    semana: int,
    params: Optional[ParametrosReferenciaSemana],
    peso_inicial_g: Optional[Decimal],
    peso_real_g: Optional[Decimal],
    poblacion: int,
    biomasa_esperada_kg: Optional[Decimal] = None,
    pendientes: dict[str, str],
) -> ResultadoRacionLote:
    return ResultadoRacionLote(
        semana_productiva=semana,
        parametros=params,
        peso_inicial_g=peso_inicial_g,
        peso_real_g=peso_real_g,
        peso_operativo_g=None,
        peso_para_racion_g=None,
        basada_en_peso=None,
        peso_utilizado=None,
        diferencia_peso_g=None,
        poblacion=poblacion,
        biomasa_esperada_kg=biomasa_esperada_kg,
        biomasa_para_racion_kg=None,
        racion_diaria_kg=None,
        racion_diaria_g=None,
        racion_por_comida_kg=None,
        racion_por_comida_g=None,
        racion_por_comida_min_kg=None,
        racion_por_comida_max_kg=None,
        racion_por_comida_min_g=None,
        racion_por_comida_max_g=None,
        pendientes=pendientes,
    )


def _normalizar_nombre(nombre: str) -> str:
    nfd = normalize("NFD", nombre.strip())
    sin_marcas = "".join(ch for ch in nfd if category(ch) != "Mn")
    return " ".join(sin_marcas.casefold().split())


def especie_usa_tabla_maestra(nombre_comun: Optional[str]) -> bool:
    """La tabla Python solo aplica a Tilapia roja. Nunca a otra especie."""
    if not nombre_comun:
        return False
    return _normalizar_nombre(nombre_comun) == _normalizar_nombre(ESPECIE_REFERENCIA)


def _nombre_especie(db: Session, especie_id: int) -> Optional[str]:
    fila = db.query(Especie).filter(Especie.id == especie_id).first()
    return fila.nombre_comun if fila is not None else None


def _numero_raciones_unico(r_min: Optional[int], r_max: Optional[int]) -> Optional[int]:
    if r_min is None or r_max is None:
        return None
    if r_min == r_max:
        return r_min
    return None


def texto_raciones(r_min: Optional[int], r_max: Optional[int]) -> Optional[str]:
    """Muestra el rango literal. 6 y 8 → '6–8'. Nunca un promedio."""
    if r_min is None and r_max is None:
        return None
    if r_min is None:
        return str(r_max)
    if r_max is None or r_min == r_max:
        return str(r_min)
    return f"{r_min}–{r_max}"


def resolver_parametros_semana(
    db: Session,
    especie_id: int,
    etapa_productiva_id: int,
    semana: int,
) -> Optional[ParametrosReferenciaSemana]:
    """Única fuente: referencias_produccion. Especie + semana. Etapa solo desempata.

    Sin fila activa → None (N/D). No usa referencia_alimentacion_tilapia.py.
    """
    if semana < 1:
        return None

    ref_bd: ReferenciaProduccion | None = ref_svc.resolver_referencia_aplicable(
        db, especie_id, etapa_productiva_id, semana
    )
    if ref_bd is None:
        return None

    peso = Decimal(str(ref_bd.peso_esperado_g)) if ref_bd.peso_esperado_g is not None else None
    tasa = (
        Decimal(str(ref_bd.tasa_alimentacion_pct))
        if ref_bd.tasa_alimentacion_pct is not None
        else None
    )
    if peso is None and tasa is None:
        return None

    r_min = int(ref_bd.raciones_min) if ref_bd.raciones_min is not None else None
    r_max = int(ref_bd.raciones_max) if ref_bd.raciones_max is not None else None
    alimento_1000 = None
    if peso is not None and tasa is not None:
        alimento_1000 = calcular_racion_kg(
            calcular_biomasa_kg(BASE_PECES_REFERENCIA, peso),
            tasa,
        )

    return ParametrosReferenciaSemana(
        semana=semana,
        fase=ref_bd.fase,
        peso_esperado_g=peso,
        tasa_alimentacion_pct=tasa,
        raciones_texto=texto_raciones(r_min, r_max),
        raciones_min=r_min,
        raciones_max=r_max,
        numero_raciones_diarias=_numero_raciones_unico(r_min, r_max),
        alimento_referencia_1000_peces_kg=alimento_1000,
        referencia_bd_id=ref_bd.id,
        fuente=FUENTE_BD,
    )


resolver_referencia_produccion = resolver_parametros_semana


def filas_catalogo_oficial(db: Session, especie_id: int) -> list[dict]:
    """Filas activas de referencias_produccion, una por rango (oficial: semana exacta)."""
    refs = (
        db.query(ReferenciaProduccion)
        .filter(
            ReferenciaProduccion.especie_id == especie_id,
            ReferenciaProduccion.activo.is_(True),
        )
        .order_by(ReferenciaProduccion.semana_desde.asc(), ReferenciaProduccion.id.asc())
        .all()
    )
    filas = []
    for ref in refs:
        peso = Decimal(str(ref.peso_esperado_g)) if ref.peso_esperado_g is not None else Decimal("0")
        tasa = (
            Decimal(str(ref.tasa_alimentacion_pct))
            if ref.tasa_alimentacion_pct is not None
            else Decimal("0")
        )
        r_min = int(ref.raciones_min) if ref.raciones_min is not None else None
        r_max = int(ref.raciones_max) if ref.raciones_max is not None else None
        alimento = calcular_racion_kg(calcular_biomasa_kg(BASE_PECES_REFERENCIA, peso), tasa)
        filas.append(
            {
                "semana": ref.semana_desde,
                "fase": ref.fase or "",
                "peso_esperado_g": peso,
                "tasa_alimentacion_pct": tasa,
                "raciones_diarias": texto_raciones(r_min, r_max) or "N/D",
                "raciones_min": r_min if r_min is not None else 0,
                "raciones_max": r_max if r_max is not None else (r_min or 0),
                "numero_raciones_diarias": _numero_raciones_unico(r_min, r_max),
                "alimento_referencia_1000_peces_kg": alimento,
            }
        )
    return filas


def calcular_racion_lote(
    db: Session,
    lote: Lote,
    *,
    dias_cultivo: int,
    peso_inicial_g: Optional[Decimal],
    peso_real_g: Optional[Decimal],
) -> ResultadoRacionLote:
    semana = semana_productiva_alimentacion(dias_cultivo)
    params = resolver_parametros_semana(
        db, lote.especie_id, lote.etapa_productiva_id, semana
    )
    poblacion = obtener_poblacion_disponible(db, lote.id, lote.cantidad_sembrada)
    pendientes: dict[str, str] = {}

    if params is None:
        pendientes["racion_diaria_recomendada_kg"] = MOTIVO_SIN_REFERENCIA
        pendientes["numero_raciones_diarias"] = MOTIVO_SIN_REFERENCIA
        return _resultado_sin_calculo(
            semana=semana,
            params=None,
            peso_inicial_g=peso_inicial_g,
            peso_real_g=peso_real_g,
            poblacion=poblacion,
            pendientes=pendientes,
        )

    biomasa_esperada = (
        calcular_biomasa_kg(poblacion, params.peso_esperado_g)
        if params.peso_esperado_g is not None
        else None
    )

    peso_operativo = peso_operativo_lote(peso_inicial_g, peso_real_g)
    if peso_real_g is not None:
        basada_en = BASADA_EN_PESO_REAL
        peso_utilizado = PESO_UTILIZADO_REAL
    elif peso_inicial_g is not None:
        basada_en = BASADA_EN_PESO_INICIAL
        peso_utilizado = PESO_UTILIZADO_INICIAL
    else:
        basada_en = None
        peso_utilizado = None

    if peso_operativo is None:
        pendientes["racion_diaria_recomendada_kg"] = MOTIVO_SIN_PESO_OPERATIVO
        return _resultado_sin_calculo(
            semana=semana,
            params=params,
            peso_inicial_g=peso_inicial_g,
            peso_real_g=peso_real_g,
            poblacion=poblacion,
            biomasa_esperada_kg=biomasa_esperada,
            pendientes=pendientes,
        )

    biomasa_racion = calcular_biomasa_kg(poblacion, peso_operativo)
    diferencia = (
        _d2(peso_operativo - params.peso_esperado_g)
        if params.peso_esperado_g is not None
        else None
    )

    racion = None
    racion_g = None
    if params.tasa_alimentacion_pct is not None:
        racion, racion_g = calcular_racion_operativa(biomasa_racion, params.tasa_alimentacion_pct)
    else:
        pendientes["racion_diaria_recomendada_kg"] = MOTIVO_SIN_TASA

    if params.numero_raciones_diarias is None:
        if params.raciones_texto:
            pendientes["numero_raciones_diarias"] = "RACIONES_EN_RANGO"
        else:
            pendientes["numero_raciones_diarias"] = MOTIVO_SIN_RACIONES

    racion_comida = None
    racion_comida_g = None
    racion_min_kg = None
    racion_max_kg = None
    racion_min_g = None
    racion_max_g = None
    if racion is not None and racion_g is not None:
        (
            racion_comida,
            racion_comida_g,
            racion_min_kg,
            racion_max_kg,
            racion_min_g,
            racion_max_g,
        ) = calcular_alimento_por_racion(
            racion, racion_g, params.raciones_min, params.raciones_max
        )

    return ResultadoRacionLote(
        semana_productiva=semana,
        parametros=params,
        peso_inicial_g=peso_inicial_g,
        peso_real_g=peso_real_g,
        peso_operativo_g=peso_operativo,
        peso_para_racion_g=peso_operativo,
        basada_en_peso=basada_en,
        peso_utilizado=peso_utilizado,
        diferencia_peso_g=diferencia,
        poblacion=poblacion,
        biomasa_esperada_kg=biomasa_esperada,
        biomasa_para_racion_kg=biomasa_racion,
        racion_diaria_kg=racion,
        racion_diaria_g=racion_g,
        racion_por_comida_kg=racion_comida,
        racion_por_comida_g=racion_comida_g,
        racion_por_comida_min_kg=racion_min_kg,
        racion_por_comida_max_kg=racion_max_kg,
        racion_por_comida_min_g=racion_min_g,
        racion_por_comida_max_g=racion_max_g,
        pendientes=pendientes,
    )


def _peso_biometria_hasta(
    bio_fechas: list[datetime],
    bio_pesos: list[Decimal],
    momento: datetime,
) -> Optional[Decimal]:
    indice = bisect_right(bio_fechas, momento) - 1
    if indice < 0:
        return None
    return bio_pesos[indice]


def calcular_racion_en_fecha(
    db: Session,
    lote: Lote,
    *,
    fecha: date,
    poblacion: int,
    peso_real_hasta: Optional[Decimal],
    peso_inicial_g: Optional[Decimal] = None,
) -> Optional[Decimal]:
    dias = max(0, (fecha - lote.fecha_siembra).days)
    semana = semana_productiva_alimentacion(dias)
    params = resolver_parametros_semana(
        db, lote.especie_id, lote.etapa_productiva_id, semana
    )
    if params is None or params.tasa_alimentacion_pct is None:
        return None
    peso = peso_operativo_lote(peso_inicial_g, peso_real_hasta)
    if peso is None:
        return None
    biomasa = calcular_biomasa_kg(poblacion, peso)
    racion_kg, _racion_g = calcular_racion_operativa(biomasa, params.tasa_alimentacion_pct)
    return racion_kg


def construir_serie_alimentacion_comparativa(
    db: Session,
    lote: Lote,
    *,
    sembrados: int,
    acum_morts,
    acum_cosechas,
    bio_fechas: list[datetime],
    bio_pesos: list[Decimal],
    alimentacion_por_dia: dict[date, Decimal],
) -> list[dict]:
    """Real vs recomendada por día; la recomendada usa la referencia de ESA semana."""
    from app.services.analisis_service import _poblacion_as_of

    puntos: list[dict] = []
    for fecha in sorted(alimentacion_por_dia):
        real = alimentacion_por_dia[fecha]
        momento = datetime.combine(fecha, time.max, tzinfo=TZ)
        poblacion, _, _ = _poblacion_as_of(sembrados, acum_morts, acum_cosechas, momento)
        peso_hasta = _peso_biometria_hasta(bio_fechas, bio_pesos, momento)
        peso_inicial = (
            Decimal(str(lote.peso_inicial_promedio_g))
            if lote.peso_inicial_promedio_g is not None
            else None
        )
        recomendada = calcular_racion_en_fecha(
            db,
            lote,
            fecha=fecha,
            poblacion=poblacion,
            peso_real_hasta=peso_hasta,
            peso_inicial_g=peso_inicial,
        )
        desviacion = None
        desviacion_pct = None
        if recomendada is not None:
            desviacion = _d3(real - recomendada)
            if recomendada != 0:
                desviacion_pct = _d2((real - recomendada) / recomendada * CIEN)
        dias = max(0, (fecha - lote.fecha_siembra).days)
        puntos.append(
            {
                "fecha": fecha,
                "real_kg": real,
                "recomendada_kg": recomendada,
                "desviacion_kg": desviacion,
                "desviacion_porcentaje": desviacion_pct,
                "semana_cultivo": semana_productiva_alimentacion(dias),
            }
        )
    return puntos


def fila_maestra_a_dict(fila: FilaReferenciaAlimentacion) -> dict:
    return {
        "semana": fila.semana,
        "fase": fila.fase,
        "peso_esperado_g": fila.peso_esperado_g,
        "tasa_alimentacion_pct": fila.tasa_alimentacion_pct,
        "raciones_diarias": fila.raciones_texto,
        "raciones_min": fila.raciones_min,
        "raciones_max": fila.raciones_max,
        "numero_raciones_diarias": fila.numero_raciones_unico,
        "alimento_referencia_1000_peces_kg": fila.alimento_referencia_1000_peces_kg,
    }


def comparar_tabla_maestra_con_bd(db: Session, especie_id: int, etapa_preferida_id: int) -> list[dict]:
    """Solo lectura. Una fila por semana 1–24: Python vs BD resuelta."""
    filas = []
    for fila in TABLA_ALIMENTACION_TILAPIA:
        ref = ref_svc.resolver_referencia_aplicable(
            db, especie_id, etapa_preferida_id, fila.semana
        )
        peso_bd = Decimal(str(ref.peso_esperado_g)) if ref and ref.peso_esperado_g is not None else None
        tasa_bd = (
            Decimal(str(ref.tasa_alimentacion_pct))
            if ref and ref.tasa_alimentacion_pct is not None
            else None
        )
        r_min = int(ref.raciones_min) if ref is not None and ref.raciones_min is not None else None
        r_max = int(ref.raciones_max) if ref is not None and ref.raciones_max is not None else None
        raciones_bd = texto_raciones(r_min, r_max)
        fase_bd = ref.fase if ref is not None else None
        filas.append(
            {
                "semana": fila.semana,
                "peso_python": fila.peso_esperado_g,
                "peso_bd": peso_bd,
                "tasa_python": fila.tasa_alimentacion_pct,
                "tasa_bd": tasa_bd,
                "raciones_python": fila.raciones_texto,
                "raciones_bd": raciones_bd,
                "fase_python": fila.fase,
                "fase_bd": fase_bd,
                "referencia_bd_id": ref.id if ref else None,
                "coincide_peso": peso_bd == fila.peso_esperado_g if peso_bd is not None else False,
                "coincide_tasa": tasa_bd == fila.tasa_alimentacion_pct if tasa_bd is not None else False,
                "coincide_raciones": raciones_bd == fila.raciones_texto if raciones_bd is not None else False,
                "coincide_fase": fase_bd == fila.fase if fase_bd is not None else False,
            }
        )
    return filas
