"""Validaciones temporales comunes para eventos operativos reales."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException

TZ_COLOMBIA = ZoneInfo("America/Bogota")


def validar_no_futuro(fecha_hora: datetime, nombre_evento: str = "El evento") -> None:
    """Rechaza eventos futuros y normaliza datetimes sin zona para evitar errores de comparación."""
    if fecha_hora.tzinfo is None:
        # Los formularios del frontend pueden enviar hora local sin offset.
        # Se interpreta como hora de Colombia, que es la zona operativa del ERP.
        fecha_hora = fecha_hora.replace(tzinfo=TZ_COLOMBIA)
    if fecha_hora.astimezone(timezone.utc) > datetime.now(timezone.utc):
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
