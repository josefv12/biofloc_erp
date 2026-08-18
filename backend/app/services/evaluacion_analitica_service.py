"""Motor reusable de evaluación analítica explicable.

Este módulo no calcula indicadores productivos: recibe valores ya calculados
por ``analisis_service`` y los contrasta con objetivos o rangos existentes.
Mantiene separados el estado analítico y el cumplimiento de rango. En
particular, una medición fuera de rango no se convierte en ALERTA o CRITICO
porque el modelo actual no define zonas de severidad.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.schemas.analisis import (
    CumplimientoRango,
    EstadoAnalitico,
    EvaluacionIndicadorOut,
    RecomendacionAnaliticaOut,
)

D2 = Decimal("0.01")
D6 = Decimal("0.000001")
CIEN = Decimal("100")

MOTIVO_SIN_DATOS = "SIN_DATOS"
MOTIVO_SIN_REFERENCIA = "SIN_REFERENCIA"
MOTIVO_OBJETIVO_CERO = "OBJETIVO_CERO"
MOTIVO_FUERA_RANGO = "VALOR_FUERA_DE_RANGO_CONFIGURADO"


def _d6(valor: Decimal) -> Decimal:
    return valor.quantize(D6, rounding=ROUND_HALF_UP)


def _porcentaje(diferencia: Decimal, base: Decimal) -> Optional[Decimal]:
    if base == 0:
        return None
    return (diferencia / base * CIEN).quantize(D2, rounding=ROUND_HALF_UP)


def evaluar_objetivo(
    *,
    indicador: str,
    etiqueta: str,
    real: Optional[Decimal],
    objetivo: Optional[Decimal],
    unidad: Optional[str],
    referencia: Optional[str] = None,
    fecha_real: Optional[date] = None,
    fecha_referencia: Optional[date] = None,
    motivo_sin_datos: str = MOTIVO_SIN_DATOS,
    motivo_sin_referencia: str = MOTIVO_SIN_REFERENCIA,
) -> EvaluacionIndicadorOut:
    """Contrasta real y objetivo sin asignar una valoración cualitativa."""
    if real is None:
        return EvaluacionIndicadorOut(
            indicador=indicador,
            etiqueta=etiqueta,
            objetivo=objetivo,
            unidad=unidad,
            estado_analitico=EstadoAnalitico.SIN_DATOS,
            motivo=motivo_sin_datos,
            explicacion=f"No hay un valor real disponible para {etiqueta}.",
            referencia=referencia,
            fecha_real=fecha_real,
            fecha_referencia=fecha_referencia,
        )
    if objetivo is None:
        return EvaluacionIndicadorOut(
            indicador=indicador,
            etiqueta=etiqueta,
            real=real,
            unidad=unidad,
            estado_analitico=EstadoAnalitico.SIN_REFERENCIA,
            motivo=motivo_sin_referencia,
            explicacion=(
                f"{etiqueta} tiene un valor real de {_d6(real)}"
                f"{f' {unidad}' if unidad else ''}, pero no existe un objetivo configurado."
            ),
            referencia=referencia,
            fecha_real=fecha_real,
            fecha_referencia=fecha_referencia,
        )

    diferencia = _d6(real - objetivo)
    porcentaje = _porcentaje(diferencia, objetivo)
    motivo = MOTIVO_OBJETIVO_CERO if objetivo == 0 else None
    texto_pct = (
        f" ({porcentaje} %)" if porcentaje is not None else " (porcentaje no calculable: objetivo 0)"
    )
    return EvaluacionIndicadorOut(
        indicador=indicador,
        etiqueta=etiqueta,
        real=real,
        objetivo=objetivo,
        unidad=unidad,
        diferencia_objetivo=diferencia,
        diferencia_objetivo_porcentaje=porcentaje,
        motivo=motivo,
        explicacion=(
            f"Real {_d6(real)} frente a objetivo {_d6(objetivo)}"
            f"{f' {unidad}' if unidad else ''}; diferencia {_d6(diferencia)}{texto_pct}. "
            "La desviación es descriptiva y no clasifica el resultado."
        ),
        referencia=referencia,
        fecha_real=fecha_real,
        fecha_referencia=fecha_referencia,
    )


def evaluar_rango(
    *,
    indicador: str,
    etiqueta: str,
    real: Optional[Decimal],
    minimo: Optional[Decimal],
    maximo: Optional[Decimal],
    unidad: Optional[str],
    referencia: Optional[str] = None,
    fecha_real: Optional[date] = None,
) -> EvaluacionIndicadorOut:
    """Evalúa un rango inclusivo sin inventar bandas de severidad."""
    if real is None:
        return EvaluacionIndicadorOut(
            indicador=indicador,
            etiqueta=etiqueta,
            minimo=minimo,
            maximo=maximo,
            unidad=unidad,
            estado_analitico=EstadoAnalitico.SIN_DATOS,
            motivo=MOTIVO_SIN_DATOS,
            explicacion=f"No hay una medición disponible para {etiqueta}.",
            referencia=referencia,
            fecha_real=fecha_real,
        )
    if minimo is None and maximo is None:
        return EvaluacionIndicadorOut(
            indicador=indicador,
            etiqueta=etiqueta,
            real=real,
            unidad=unidad,
            estado_analitico=EstadoAnalitico.SIN_REFERENCIA,
            motivo=MOTIVO_SIN_REFERENCIA,
            explicacion=(
                f"{etiqueta} registra {_d6(real)}{f' {unidad}' if unidad else ''}, "
                "pero no existe un rango configurado."
            ),
            referencia=referencia,
            fecha_real=fecha_real,
        )

    limite: Optional[Decimal] = None
    if minimo is not None and real < minimo:
        limite = minimo
    elif maximo is not None and real > maximo:
        limite = maximo

    if limite is None:
        return EvaluacionIndicadorOut(
            indicador=indicador,
            etiqueta=etiqueta,
            real=real,
            minimo=minimo,
            maximo=maximo,
            unidad=unidad,
            desviacion_rango=Decimal("0"),
            desviacion_rango_porcentaje=Decimal("0"),
            cumplimiento_rango=CumplimientoRango.DENTRO_RANGO,
            explicacion=(
                f"El valor real {_d6(real)}{f' {unidad}' if unidad else ''} está dentro "
                "del rango configurado."
            ),
            referencia=referencia,
            fecha_real=fecha_real,
        )

    desviacion = _d6(real - limite)
    porcentaje = _porcentaje(desviacion, limite)
    direccion = "por debajo del mínimo" if desviacion < 0 else "por encima del máximo"
    return EvaluacionIndicadorOut(
        indicador=indicador,
        etiqueta=etiqueta,
        real=real,
        minimo=minimo,
        maximo=maximo,
        unidad=unidad,
        desviacion_rango=desviacion,
        desviacion_rango_porcentaje=porcentaje,
        cumplimiento_rango=CumplimientoRango.FUERA_RANGO,
        motivo=MOTIVO_FUERA_RANGO,
        explicacion=(
            f"El valor real {_d6(real)}{f' {unidad}' if unidad else ''} está {direccion} "
            f"configurado ({_d6(limite)}{f' {unidad}' if unidad else ''}) por "
            f"{abs(desviacion)}{f' {unidad}' if unidad else ''}. No se asigna severidad "
            "porque no existen zonas de alerta o criticidad configuradas."
        ),
        referencia=referencia,
        fecha_real=fecha_real,
    )


def recomendacion_agua(
    evaluacion: EvaluacionIndicadorOut,
) -> Optional[RecomendacionAnaliticaOut]:
    """Recomienda revisión operativa solo ante un rango formal incumplido."""
    if evaluacion.cumplimiento_rango != CumplimientoRango.FUERA_RANGO:
        return None
    return RecomendacionAnaliticaOut(
        indicador=evaluacion.indicador,
        estado_analitico=evaluacion.estado_analitico,
        cumplimiento_rango=evaluacion.cumplimiento_rango,
        motivo=evaluacion.explicacion,
        recomendacion=(
            f"Revisar la medición y el control operativo de {evaluacion.etiqueta} "
            "según el protocolo vigente. La aplicación no propone cantidades ni "
            "acciones automáticas."
        ),
    )
