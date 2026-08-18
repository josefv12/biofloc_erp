"""Consulta de referencias_produccion (tabla DDL existente). Solo GET en esta fase."""
from typing import Iterable, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.referencia_produccion import ReferenciaProduccion


def listar_referencias_produccion(
    db: Session,
    especie_id: Optional[int] = None,
    etapa_productiva_id: Optional[int] = None,
    semana: Optional[int] = None,
    solo_activos: bool = False,
) -> list[ReferenciaProduccion]:
    q = db.query(ReferenciaProduccion)
    if especie_id is not None:
        q = q.filter(ReferenciaProduccion.especie_id == especie_id)
    if etapa_productiva_id is not None:
        q = q.filter(ReferenciaProduccion.etapa_productiva_id == etapa_productiva_id)
    if semana is not None:
        q = q.filter(
            ReferenciaProduccion.semana_desde <= semana,
            ReferenciaProduccion.semana_hasta >= semana,
        )
    if solo_activos:
        q = q.filter(ReferenciaProduccion.activo.is_(True))
    return q.order_by(
        ReferenciaProduccion.especie_id.asc(),
        ReferenciaProduccion.etapa_productiva_id.asc(),
        ReferenciaProduccion.semana_desde.asc(),
    ).all()


def _precedencia(referencia: ReferenciaProduccion) -> tuple[int, int, int]:
    """Orden de especificidad: rango más estrecho, luego el que empieza más tarde."""
    amplitud = referencia.semana_hasta - referencia.semana_desde
    return (amplitud, -referencia.semana_desde, referencia.id)


def _candidatas_activas(
    db: Session, especie_id: int, etapa_productiva_id: int
) -> list[ReferenciaProduccion]:
    return (
        db.query(ReferenciaProduccion)
        .filter(
            ReferenciaProduccion.especie_id == especie_id,
            ReferenciaProduccion.etapa_productiva_id == etapa_productiva_id,
            ReferenciaProduccion.activo.is_(True),
        )
        .all()
    )


def _resolver(
    candidatas: list[ReferenciaProduccion], semana: int
) -> Optional[ReferenciaProduccion]:
    aplicables = [
        r for r in candidatas if r.semana_desde <= semana <= r.semana_hasta
    ]
    if not aplicables:
        return None
    return min(aplicables, key=_precedencia)


def resolver_referencia_aplicable(
    db: Session,
    especie_id: int,
    etapa_productiva_id: int,
    semana: int,
) -> Optional[ReferenciaProduccion]:
    """Referencia vigente para especie + etapa + semana, o None si no existe.

    Los rangos [semana_desde, semana_hasta] pueden solaparse, así que ante
    varias coincidencias se toma la de rango más estrecho (la más específica)
    y, a igual amplitud, la que empieza más tarde.
    """
    return _resolver(_candidatas_activas(db, especie_id, etapa_productiva_id), semana)


def resolver_referencias_por_semana(
    db: Session,
    especie_id: int,
    etapa_productiva_id: int,
    semanas: Iterable[int],
) -> dict[int, Optional[ReferenciaProduccion]]:
    """Resuelve varias semanas con una sola consulta y la misma precedencia.

    Sirve para recorrer el historial de un lote: cada semana de cultivo se
    resuelve por separado, nunca con la referencia de la semana actual.
    """
    candidatas = _candidatas_activas(db, especie_id, etapa_productiva_id)
    return {semana: _resolver(candidatas, semana) for semana in set(semanas)}


def obtener_referencia_produccion(db: Session, referencia_id: int) -> ReferenciaProduccion:
    row = db.query(ReferenciaProduccion).filter(ReferenciaProduccion.id == referencia_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Referencia de producción no encontrada")
    return row
