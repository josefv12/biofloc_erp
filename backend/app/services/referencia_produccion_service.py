"""Consulta y administración de referencias_produccion (tabla DDL existente)."""
import logging
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.lote import Especie, EtapaProductiva
from app.models.referencia_produccion import ReferenciaProduccion
from app.schemas.referencia_produccion import ReferenciaProduccionCreate, ReferenciaProduccionUpdate

logger = logging.getLogger(__name__)


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


def _precedencia(
    referencia: ReferenciaProduccion,
    semana: int,
    etapa_preferida_id: Optional[int] = None,
) -> tuple[int, int, int, int, int]:
    """Orden de especificidad para una semana concreta.

    1. Rango de una sola semana que coincide exactamente (semana_desde == semana == semana_hasta).
    2. Rango cuya semana_hasta coincide con la semana buscada (convención [n-1, n] → semana n).
    3. Rango más estrecho.
    4. Misma etapa que el lote, solo como desempate (la etapa del lote no filtra).
    5. El que empieza más tarde (más específico en el tiempo).
    """
    exacta = (
        0
        if referencia.semana_desde == referencia.semana_hasta == semana
        else 1
    )
    ancla_fin = 0 if referencia.semana_hasta == semana else 1
    amplitud = referencia.semana_hasta - referencia.semana_desde
    etapa_ref = getattr(referencia, "etapa_productiva_id", None)
    misma_etapa = (
        0
        if etapa_preferida_id is not None and etapa_ref == etapa_preferida_id
        else 1
    )
    return (exacta, ancla_fin, amplitud, misma_etapa, -referencia.semana_desde)


def _candidatas_activas(
    db: Session, especie_id: int
) -> list[ReferenciaProduccion]:
    """Todas las filas activas de la especie. La etapa del lote no excluye fases."""
    return (
        db.query(ReferenciaProduccion)
        .filter(
            ReferenciaProduccion.especie_id == especie_id,
            ReferenciaProduccion.activo.is_(True),
        )
        .all()
    )


def _resolver(
    candidatas: list[ReferenciaProduccion],
    semana: int,
    etapa_preferida_id: Optional[int] = None,
) -> Optional[ReferenciaProduccion]:
    aplicables = [
        r for r in candidatas if r.semana_desde <= semana <= r.semana_hasta
    ]
    if not aplicables:
        return None
    if len(aplicables) > 1:
        logger.warning(
            "Varias referencias activas coinciden con semana %s (ids=%s); "
            "se aplica la de mayor especificidad.",
            semana,
            [r.id for r in aplicables],
        )
    return min(
        aplicables,
        key=lambda referencia: _precedencia(referencia, semana, etapa_preferida_id),
    )


def resolver_referencia_aplicable(
    db: Session,
    especie_id: int,
    etapa_productiva_id: int,
    semana: int,
) -> Optional[ReferenciaProduccion]:
    """Referencia vigente para especie + semana. Etapa solo desempata empates.

    Los rangos [semana_desde, semana_hasta] pueden solaparse, así que ante
    varias coincidencias se toma la de rango más estrecho (la más específica)
    y, a igual amplitud, la de la misma etapa del lote y la que empieza más tarde.
    """
    return _resolver(_candidatas_activas(db, especie_id), semana, etapa_productiva_id)


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
    candidatas = _candidatas_activas(db, especie_id)
    return {
        semana: _resolver(candidatas, semana, etapa_productiva_id)
        for semana in set(semanas)
    }


def obtener_referencia_produccion(db: Session, referencia_id: int) -> ReferenciaProduccion:
    row = db.query(ReferenciaProduccion).filter(ReferenciaProduccion.id == referencia_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Referencia de producción no encontrada")
    return row


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="referencias_produccion",
            registro_id=registro_id,
            accion=accion,
            detalle=detalle,
        )
    )


def _serializar_auditoria(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _detalle_auditoria(cambios: dict) -> dict:
    return {k: _serializar_auditoria(v) for k, v in cambios.items()}


def _validar_fks(db: Session, especie_id: int, etapa_productiva_id: int) -> None:
    if not db.query(Especie).filter(Especie.id == especie_id).first():
        raise HTTPException(status_code=404, detail=f"Especie id={especie_id} no existe")
    if not db.query(EtapaProductiva).filter(EtapaProductiva.id == etapa_productiva_id).first():
        raise HTTPException(
            status_code=404,
            detail=f"Etapa productiva id={etapa_productiva_id} no existe",
        )


def _validar_rango(semana_desde: int, semana_hasta: int) -> None:
    if semana_desde < 0:
        raise HTTPException(status_code=422, detail="semana_desde debe ser >= 0")
    if semana_hasta < semana_desde:
        raise HTTPException(status_code=422, detail="semana_hasta debe ser >= semana_desde")


def _conflicto_unico(
    db: Session,
    especie_id: int,
    etapa_productiva_id: int,
    semana_desde: int,
    semana_hasta: int,
    excluir_id: Optional[int] = None,
) -> bool:
    q = db.query(ReferenciaProduccion).filter(
        ReferenciaProduccion.especie_id == especie_id,
        ReferenciaProduccion.etapa_productiva_id == etapa_productiva_id,
        ReferenciaProduccion.semana_desde == semana_desde,
        ReferenciaProduccion.semana_hasta == semana_hasta,
    )
    if excluir_id is not None:
        q = q.filter(ReferenciaProduccion.id != excluir_id)
    return q.first() is not None


def crear_referencia_produccion(
    db: Session, data: ReferenciaProduccionCreate, usuario_id: int
) -> ReferenciaProduccion:
    _validar_fks(db, data.especie_id, data.etapa_productiva_id)
    _validar_rango(data.semana_desde, data.semana_hasta)
    if _conflicto_unico(
        db, data.especie_id, data.etapa_productiva_id, data.semana_desde, data.semana_hasta
    ):
        raise HTTPException(
            status_code=409,
            detail="Ya existe una referencia de producción para esa especie, etapa y rango de semanas",
        )

    nuevo = ReferenciaProduccion(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una referencia de producción para esa especie, etapa y rango de semanas",
        )

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {
            "especie_id": nuevo.especie_id,
            "etapa_productiva_id": nuevo.etapa_productiva_id,
            "semana_desde": nuevo.semana_desde,
            "semana_hasta": nuevo.semana_hasta,
            "activo": nuevo.activo,
        },
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_referencia_produccion(
    db: Session,
    referencia_id: int,
    data: ReferenciaProduccionUpdate,
    usuario_id: int,
) -> ReferenciaProduccion:
    row = obtener_referencia_produccion(db, referencia_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return row

    especie_id = cambios.get("especie_id", row.especie_id)
    etapa_id = cambios.get("etapa_productiva_id", row.etapa_productiva_id)
    semana_desde = cambios.get("semana_desde", row.semana_desde)
    semana_hasta = cambios.get("semana_hasta", row.semana_hasta)

    if "especie_id" in cambios or "etapa_productiva_id" in cambios:
        _validar_fks(db, especie_id, etapa_id)
    _validar_rango(semana_desde, semana_hasta)

    if _conflicto_unico(db, especie_id, etapa_id, semana_desde, semana_hasta, excluir_id=row.id):
        raise HTTPException(
            status_code=409,
            detail="Ya existe una referencia de producción para esa especie, etapa y rango de semanas",
        )

    for key, value in cambios.items():
        setattr(row, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una referencia de producción para esa especie, etapa y rango de semanas",
        )

    _registrar_auditoria(
        db,
        usuario_id,
        "UPDATE",
        row.id,
        _detalle_auditoria(cambios),
    )
    db.commit()
    db.refresh(row)
    return row
