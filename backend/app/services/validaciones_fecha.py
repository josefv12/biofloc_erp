"""Validaciones temporales comunes para eventos operativos reales."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException

TZ_COLOMBIA = ZoneInfo("America/Bogota")


def validar_no_futuro(fecha_hora: datetime, nombre_evento: str = "El evento") -> None:
    """Rechaza eventos operativos con fecha/hora posterior al momento actual."""
    if fecha_hora > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=422,
            detail=f"{nombre_evento} no puede registrarse con fecha/hora futura",
        )


def validar_fecha_no_futura(fecha: date, nombre_evento: str = "La fecha") -> None:
    """Rechaza fechas operativas posteriores a la fecha actual en Colombia."""
    hoy_colombia = datetime.now(TZ_COLOMBIA).date()
    if fecha > hoy_colombia:
        raise HTTPException(
            status_code=422,
            detail=f"{nombre_evento} no puede ser una fecha futura",
        )
