"""
Tabla histórica de alimentación — tilapia roja Biofloc (20 semanas / 5 meses).

El catálogo oficial en runtime es `referencias_produccion` (Etapa 6C).
Este archivo NO es fallback del resolver. Se conserva para calendario
(`semana_productiva_alimentacion`) y comparación de solo lectura.

No eliminar todavía.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

VERSION = "2026-11-23-tilapia-roja-20s"
ESPECIE_REFERENCIA = "Tilapia roja"
SEMANA_MIN = 1
SEMANA_MAX = 20
BASE_PECES_REFERENCIA = 1000


@dataclass(frozen=True, slots=True)
class FilaReferenciaAlimentacion:
    semana: int
    fase: str
    peso_esperado_g: Decimal
    tasa_alimentacion_pct: Decimal
    raciones_texto: str
    raciones_min: int
    raciones_max: int

    @property
    def numero_raciones_unico(self) -> int | None:
        """Número de raciones solo si la referencia no es un rango."""
        if self.raciones_min == self.raciones_max:
            return self.raciones_min
        return None

    @property
    def alimento_referencia_1000_peces_kg(self) -> Decimal:
        """Biomasa de 1 000 peces × tasa / 100."""
        biomasa_kg = self.peso_esperado_g * Decimal(BASE_PECES_REFERENCIA) / Decimal("1000")
        return (biomasa_kg * self.tasa_alimentacion_pct / Decimal("100")).quantize(Decimal("0.001"))


def _fila(
    semana: int,
    fase: str,
    peso: str,
    tasa: str,
    raciones: str,
) -> FilaReferenciaAlimentacion:
    partes = raciones.split("-")
    r_min = int(partes[0])
    r_max = int(partes[1]) if len(partes) > 1 else r_min
    return FilaReferenciaAlimentacion(
        semana=semana,
        fase=fase,
        peso_esperado_g=Decimal(peso),
        tasa_alimentacion_pct=Decimal(tasa),
        raciones_texto=raciones.replace("-", "–"),
        raciones_min=r_min,
        raciones_max=r_max,
    )


TABLA_ALIMENTACION_TILAPIA: tuple[FilaReferenciaAlimentacion, ...] = (
    _fila(1, "Inicio", "6.0", "13.333", "8"),
    _fila(2, "Inicio", "12.0", "9.217", "7"),
    _fila(3, "Inicio", "22.0", "7.143", "6"),
    _fila(4, "Inicio", "34.0", "5.583", "6"),
    _fila(5, "Levante", "45.0", "4.261", "5"),
    _fila(6, "Levante", "58.0", "3.596", "5"),
    _fila(7, "Levante", "72.0", "3.218", "4"),
    _fila(8, "Levante", "87.0", "2.935", "4"),
    _fila(9, "Levante", "105.0", "2.868", "4"),
    _fila(10, "Levante", "125.0", "2.730", "4"),
    _fila(11, "Engorde", "150.0", "2.774", "3"),
    _fila(12, "Engorde", "175.0", "2.452", "3"),
    _fila(13, "Engorde", "202.0", "2.187", "3"),
    _fila(14, "Engorde", "228.0", "1.990", "3"),
    _fila(15, "Engorde", "256.0", "1.800", "3"),
    _fila(16, "Engorde", "283.0", "1.673", "3"),
    _fila(17, "Engorde", "312.0", "1.558", "3"),
    _fila(18, "Engorde", "341.0", "1.446", "2-3"),
    _fila(19, "Engorde", "370.0", "1.367", "2-3"),
    _fila(20, "Engorde", "400.0", "1.283", "2"),
)

_MAPA_SEMANAS = {fila.semana: fila for fila in TABLA_ALIMENTACION_TILAPIA}


def semana_productiva_alimentacion(dias_cultivo: int) -> int:
    """Edad del lote en semanas desde la siembra. No es semana ISO.

    Día 0–6 → semana 1; día 7–13 → semana 2; día 14 → semana 3.
    semana = floor(días_cultivo / 7) + 1. Sin tope: después de la semana 20 no hay referencia del ciclo y debe mostrarse N/D.
    """
    dias = max(0, int(dias_cultivo))
    return dias // 7 + 1


def obtener_fila_maestra(semana: int) -> FilaReferenciaAlimentacion | None:
    """Fila exacta de la semana. No recorta a 24 ni reutiliza otra semana."""
    return _MAPA_SEMANAS.get(int(semana))


def listar_tabla_maestra() -> list[FilaReferenciaAlimentacion]:
    return list(TABLA_ALIMENTACION_TILAPIA)


def iter_semanas(semanas: Iterable[int]) -> dict[int, FilaReferenciaAlimentacion]:
    out: dict[int, FilaReferenciaAlimentacion] = {}
    for semana in semanas:
        fila = obtener_fila_maestra(semana)
        if fila is not None:
            out[semana] = fila
    return out
