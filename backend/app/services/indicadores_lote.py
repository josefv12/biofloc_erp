"""Indicadores productivos del lote. Fórmulas oficiales, sin duplicar en frontend."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from math import log, pi
from typing import Optional

D2 = Decimal("0.01")
D3 = Decimal("0.001")
D4 = Decimal("0.0001")
CIEN = Decimal("100")
MIL = Decimal("1000")

MOTIVO_SIN_BIOMETRIA = "SIN_BIOMETRIA"
MOTIVO_SIN_PESO_INICIAL = "SIN_PESO_INICIAL_LOTE"
MOTIVO_DIAS_CERO = "DIAS_CULTIVO_CERO"
MOTIVO_SGR = "SGR_REQUIERE_PESOS_POSITIVOS_Y_DIAS"
MOTIVO_SIN_VOLUMEN = "SIN_VOLUMEN_UTIL_ESTANQUE"
MOTIVO_SIN_BIOMASA_ACTUAL = "SIN_BIOMETRIA"
MOTIVO_COSECHA_SIN_PESO = "COSECHA_SIN_PESO_REGISTRADO"


def biomasa_kg(poblacion: int, peso_g: Decimal) -> Decimal:
    return (Decimal(poblacion) * peso_g / MIL).quantize(D3, rounding=ROUND_HALF_UP)


def supervivencia_biologica_pct(sembrados: int, mortalidad_acumulada: int) -> Optional[Decimal]:
    """(sembrados − mortalidad) / sembrados × 100. La cosecha no entra."""
    if sembrados <= 0:
        return None
    vivos = Decimal(sembrados - int(mortalidad_acumulada or 0))
    return (vivos / Decimal(sembrados) * CIEN).quantize(D2, rounding=ROUND_HALF_UP)


def mortalidad_pct(sembrados: int, mortalidad_acumulada: int) -> Optional[Decimal]:
    if sembrados <= 0:
        return None
    return (Decimal(int(mortalidad_acumulada or 0)) / Decimal(sembrados) * CIEN).quantize(
        D2, rounding=ROUND_HALF_UP
    )


def ganancia_diaria_g(
    ganancia: Optional[Decimal], dias_cultivo: int
) -> tuple[Optional[Decimal], Optional[str]]:
    if ganancia is None:
        return None, MOTIVO_SIN_BIOMETRIA
    if dias_cultivo <= 0:
        return None, MOTIVO_DIAS_CERO
    gpd = (ganancia / Decimal(dias_cultivo)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return gpd, None


def sgr_pct_dia(
    peso_inicial_g: Optional[Decimal],
    peso_actual_g: Optional[Decimal],
    dias_cultivo: int,
) -> tuple[Optional[Decimal], Optional[str]]:
    """SGR %/día = (ln peso_actual − ln peso_inicial) / días × 100."""
    if peso_inicial_g is None or peso_actual_g is None:
        return None, MOTIVO_SIN_BIOMETRIA if peso_actual_g is None else MOTIVO_SIN_PESO_INICIAL
    if dias_cultivo <= 0:
        return None, MOTIVO_DIAS_CERO
    if peso_inicial_g <= 0 or peso_actual_g <= 0:
        return None, MOTIVO_SGR
    valor = (log(float(peso_actual_g)) - log(float(peso_inicial_g))) / dias_cultivo * 100
    return Decimal(str(valor)).quantize(D4, rounding=ROUND_HALF_UP), None


def ganancia_biomasa_productiva_kg(
    biomasa_actual_kg: Optional[Decimal],
    biomasa_inicial_kg: Optional[Decimal],
    biomasa_cosechada_kg: Optional[Decimal],
    *,
    hay_cosecha: bool,
    cosecha_con_peso: bool,
) -> tuple[Optional[Decimal], Optional[str]]:
    """actual + cosechada − inicial. No inventa peso de cosecha."""
    if biomasa_inicial_kg is None:
        return None, MOTIVO_SIN_PESO_INICIAL
    if biomasa_actual_kg is None:
        return None, MOTIVO_SIN_BIOMASA_ACTUAL
    if hay_cosecha and not cosecha_con_peso:
        return None, MOTIVO_COSECHA_SIN_PESO
    cosechada = biomasa_cosechada_kg if biomasa_cosechada_kg is not None else Decimal("0")
    return (biomasa_actual_kg + cosechada - biomasa_inicial_kg).quantize(D3, rounding=ROUND_HALF_UP), None


def volumen_estanque_m3(
    diametro: Optional[Decimal], profundidad: Optional[Decimal]
) -> Optional[Decimal]:
    if diametro is None or profundidad is None:
        return None
    if diametro <= 0 or profundidad <= 0:
        return None
    radio = float(diametro) / 2
    return Decimal(str(pi * radio * radio * float(profundidad))).quantize(D3, rounding=ROUND_HALF_UP)


def densidad_kg_m3(
    biomasa_actual_kg: Optional[Decimal], volumen_m3: Optional[Decimal]
) -> tuple[Optional[Decimal], Optional[str]]:
    if biomasa_actual_kg is None:
        return None, MOTIVO_SIN_BIOMASA_ACTUAL
    if volumen_m3 is None or volumen_m3 <= 0:
        return None, MOTIVO_SIN_VOLUMEN
    return (biomasa_actual_kg / volumen_m3).quantize(D3, rounding=ROUND_HALF_UP), None
