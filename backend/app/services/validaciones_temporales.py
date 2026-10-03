"""Reglas temporales comunes para eventos operativos reales.

Los registros históricos pueden ser retroactivos, pero un evento real no puede
quedar fechado en el futuro porque alteraría indicadores, stock o población.
"""

from datetime import date, datetime, timezone
from fastapi import HTTPException


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def validar_evento_no_futuro(
    fecha_evento: date | datetime,
    nombre: str,
) -> None:
    """Rechaza un evento real fechado después de la fecha/hora actual."""
    if isinstance(fecha_evento, datetime):
        valor = fecha_evento
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        ahora = _ahora_utc()
        if valor > ahora:
            raise HTTPException(
                status_code=422,
                detail=f"La fecha de {nombre} no puede estar en el futuro.",
            )
        return

    if fecha_evento > _ahora_utc().date():
        raise HTTPException(
            status_code=422,
            detail=f"La fecha de {nombre} no puede estar en el futuro.",
        )


def validar_evento_lote(
    fecha_evento: date | datetime,
    fecha_siembra: date,
    nombre: str,
) -> None:
    """Valida simultáneamente siembra <= evento <= ahora."""
    fecha_evento_date = (
        fecha_evento.date() if isinstance(fecha_evento, datetime) else fecha_evento
    )
    if fecha_evento_date < fecha_siembra:
        raise HTTPException(
            status_code=422,
            detail=f"La fecha de {nombre} no puede ser anterior a la siembra del lote.",
        )
    validar_evento_no_futuro(fecha_evento, nombre)
