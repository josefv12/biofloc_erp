"""Estadística descriptiva de las series del núcleo analítico.

Solo describe la serie que recibe: n, primer valor, último, promedio, mínimo,
máximo, mediana y variación porcentual entre el primer y el último valor. No
hay regresión, correlación, intervalos de confianza, predicción ni umbrales, y
ninguna función emite juicio sobre los valores.

Mediana: valor central de la serie ordenada; con n par, promedio aritmético de
los dos valores centrales (`statistics.median` de la biblioteca estándar, sin
dependencias nuevas).

Variación porcentual: (último − primero) / primero × 100. Es null cuando la
serie tiene menos de dos valores o cuando el primer valor es 0, con la razón
técnica en `variacion_motivo`.
"""
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Iterable, Optional, Sequence

from app.schemas.analisis import StatsSerieOut

D2 = Decimal("0.01")
D6 = Decimal("0.000001")
CIEN = Decimal("100")

MOTIVO_SERIE_VACIA = "SERIE_VACIA"
MOTIVO_UN_SOLO_PUNTO = "SERIE_CON_UN_SOLO_PUNTO"
MOTIVO_PRIMER_VALOR_CERO = "PRIMER_VALOR_CERO"

DEFINICION_MEDIANA = (
    "Valor central de la serie ordenada; con n par, promedio de los dos centrales "
    "(statistics.median de la biblioteca estándar de Python)."
)
DEFINICION_VARIACION = (
    "(último − primero) / primero × 100 sobre la serie disponible. Null si n < 2 o si "
    "el primer valor es 0. Es una métrica descriptiva: no clasifica el resultado."
)
DEFINICION_ESTADISTICAS = (
    "n, primero, último, promedio, mínimo, máximo y mediana calculados en el backend "
    "sobre los valores no nulos de cada serie. Con n = 0 todo queda en null; con n = 1 "
    "no hay variación porcentual."
)


def _limpiar(valores: Iterable[Optional[Decimal]]) -> list[Decimal]:
    return [Decimal(str(v)) for v in valores if v is not None]


def _q6(valor: Decimal) -> Decimal:
    return valor.quantize(D6, rounding=ROUND_HALF_UP)


def stats_serie(
    valores: Sequence[Optional[Decimal]],
    unidad: Optional[str] = None,
) -> StatsSerieOut:
    """Estadística descriptiva de una serie, ya ordenada cronológicamente."""
    limpios = _limpiar(valores)
    n = len(limpios)
    if n == 0:
        return StatsSerieOut(unidad=unidad, n=0, variacion_motivo=MOTIVO_SERIE_VACIA)

    primero = limpios[0]
    ultimo = limpios[-1]
    promedio = _q6(sum(limpios, Decimal("0")) / Decimal(n))
    mediana = _q6(Decimal(str(median(limpios))))

    if n < 2:
        variacion, motivo = None, MOTIVO_UN_SOLO_PUNTO
    elif primero == 0:
        variacion, motivo = None, MOTIVO_PRIMER_VALOR_CERO
    else:
        variacion = ((ultimo - primero) / primero * CIEN).quantize(D2, rounding=ROUND_HALF_UP)
        motivo = None

    return StatsSerieOut(
        unidad=unidad,
        n=n,
        primero=_q6(primero),
        ultimo=_q6(ultimo),
        promedio=promedio,
        minimo=_q6(min(limpios)),
        maximo=_q6(max(limpios)),
        mediana=mediana,
        variacion_porcentual=variacion,
        variacion_motivo=motivo,
    )
