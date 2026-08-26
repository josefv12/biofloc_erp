"""Población disponible de un lote: sembrados − mortalidad − cosecha.

No altera vistas SQL. Sirve para validar altas de mortalidad y cosecha
antes de persistir, de modo que no se cree población negativa.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi import HTTPException

from app.models.cosecha import Cosecha
from app.models.lote import EstadoLote, Lote
from app.models.mortalidad import Mortalidad

RAZON_POBLACION_NEGATIVA_HISTORICA = "POBLACION_NEGATIVA_HISTORICA"
ESTADO_LOTE_ACTIVO = "ACTIVO"
ESTADO_LOTE_FINALIZADO = "FINALIZADO"


def calcular_poblacion_disponible(
    sembrados: int, mortalidad_acumulada: int, peces_cosechados: int
) -> int:
    return int(sembrados) - int(mortalidad_acumulada or 0) - int(peces_cosechados or 0)


def obtener_salidas_peces(db: Session, lote_id: int) -> tuple[int, int]:
    mortalidad = (
        db.query(func.coalesce(func.sum(Mortalidad.cantidad), 0))
        .filter(Mortalidad.lote_id == lote_id)
        .scalar()
    )
    cosechados = (
        db.query(func.coalesce(func.sum(Cosecha.cantidad_peces), 0))
        .filter(Cosecha.lote_id == lote_id)
        .scalar()
    )
    return int(mortalidad or 0), int(cosechados or 0)


def obtener_poblacion_disponible(db: Session, lote_id: int, cantidad_sembrada: int) -> int:
    mortalidad, cosechados = obtener_salidas_peces(db, lote_id)
    return calcular_poblacion_disponible(cantidad_sembrada, mortalidad, cosechados)


def mensaje_mortalidad_excede(solicitado: int, disponible: int) -> str:
    return (
        f"No se pueden registrar {solicitado} peces muertos. "
        f"La población disponible del lote es de {disponible} peces."
    )


def mensaje_cosecha_excede(solicitado: int, disponible: int) -> str:
    return (
        f"No se pueden cosechar {solicitado} peces. "
        f"La población disponible es {disponible}."
    )


def exigir_dentro_de_disponible(cantidad: int, disponible: int, mensaje: str) -> None:
    if cantidad > disponible:
        raise HTTPException(status_code=422, detail=mensaje)


def nombre_estado_lote(db: Session, lote: Lote) -> str:
    if getattr(lote, "estado", None) is not None:
        return str(lote.estado.nombre)
    estado = db.query(EstadoLote).filter(EstadoLote.id == lote.estado_id).first()
    return str(estado.nombre) if estado else ""


def exigir_lote_en_produccion(db: Session, lote: Lote) -> None:
    """Solo un lote ACTIVO admite registros productivos. El historial sigue en consulta."""
    nombre = nombre_estado_lote(db, lote)
    if nombre == ESTADO_LOTE_ACTIVO:
        return
    etiqueta = nombre if nombre else "cerrado"
    raise HTTPException(
        status_code=422,
        detail=(
            f"No se pueden registrar operaciones en un lote {etiqueta}. "
            "Solo un lote ACTIVO admite registros productivos."
        ),
    )


def obtener_estado_lote_por_nombre(db: Session, nombre: str) -> EstadoLote:
    estado = db.query(EstadoLote).filter(EstadoLote.nombre == nombre).first()
    if not estado:
        raise HTTPException(
            status_code=422,
            detail=f"No existe el estado de lote '{nombre}' en el catálogo.",
        )
    return estado


def listar_lotes_poblacion_negativa(db: Session) -> list[dict]:
    """Detecta lotes históricos con población < 0. No corrige datos."""
    filas = db.execute(
        text(
            """
            SELECT lote_id, codigo, cantidad_sembrada, mortalidad_acumulada,
                   peces_cosechados, poblacion_estimada
            FROM vista_biomasa_lotes
            WHERE poblacion_estimada < 0
            ORDER BY lote_id
            """
        )
    ).mappings()
    return [dict(fila) for fila in filas]
