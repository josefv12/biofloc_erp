"""
Tabla histórica de alimentación — tilapia roja Biofloc (24 semanas).

El catálogo oficial en runtime es `referencias_produccion` (Etapa 6C).
Este archivo NO es fallback del resolver. Se conserva para calendario
(`semana_productiva_alimentacion`) y comparación de solo lectura.

No eliminar todavía.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

VERSION = "2026-08-19-tilapia-roja-24s"
ESPECIE_REFERENCIA = "Tilapia roja"
SEMANA_MIN = 1
SEMANA_MAX = 24
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
    _fila(1, "Inicio", "1.5", "10.0", "6-8"),
    _fila(2, "Inicio", "3.0", "9.0", "6-8"),
    _fila(3, "Inicio", "6.0", "8.0", "6-8"),
    _fila(4, "Inicio", "11.5", "7.0", "6-8"),
    _fila(5, "Inicio", "18.5", "6.5", "6"),
    _fila(6, "Inicio", "26.0", "6.0", "6"),
    _fila(7, "Inicio", "35.0", "5.5", "5"),
    _fila(8, "Inicio", "45.0", "5.0", "4-5"),
    _fila(9, "Levante", "57.5", "4.5", "4"),
    _fila(10, "Levante", "75.0", "4.0", "4"),
    _fila(11, "Levante", "95.0", "3.5", "3-4"),
    _fila(12, "Levante", "117.5", "3.2", "3-4"),
    _fila(13, "Levante", "142.5", "3.0", "3-4"),
    _fila(14, "Levante", "170.0", "2.8", "3"),
    _fila(15, "Levante", "200.0", "2.6", "3"),
    _fila(16, "Levante", "232.5", "2.5", "3"),
    _fila(17, "Engorde", "265.0", "2.3", "2-3"),
    _fila(18, "Engorde", "297.5", "2.1", "2-3"),
    _fila(19, "Engorde", "332.5", "1.9", "2-3"),
    _fila(20, "Engorde", "367.5", "1.7", "2"),
    _fila(21, "Engorde", "402.5", "1.5", "2"),
    _fila(22, "Engorde", "437.5", "1.3", "2"),
    _fila(23, "Engorde", "470.0", "1.1", "2"),
    _fila(24, "Engorde", "500.0", "1.0", "2"),
)

_MAPA_SEMANAS = {fila.semana: fila for fila in TABLA_ALIMENTACION_TILAPIA}


def semana_productiva_alimentacion(dias_cultivo: int) -> int:
    """Edad del lote en semanas desde la siembra. No es semana ISO.

    Día 0–6 → semana 1; día 7–13 → semana 2; día 14 → semana 3.
    semana = floor(días_cultivo / 7) + 1. Sin tope: si no hay referencia, N/D.
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
