"""Catálogo maestro de especies. Escritura solo vía router ADMIN."""
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.auditoria import Auditoria
from app.models.lote import Especie
from app.models.referencia_agua import ReferenciaAgua
from app.models.referencia_produccion import ReferenciaProduccion
from app.schemas.catalogo_produccion import EspecieCatalogoOut, EspecieCreate, EspecieUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="especies",
            registro_id=registro_id,
            accion=accion,
            detalle=detalle,
        )
    )


def _conteos(db: Session) -> tuple[dict[int, int], dict[int, int]]:
    prod = dict(
        db.query(ReferenciaProduccion.especie_id, func.count(ReferenciaProduccion.id))
        .group_by(ReferenciaProduccion.especie_id)
        .all()
    )
    agua = dict(
        db.query(ReferenciaAgua.especie_id, func.count(ReferenciaAgua.id))
        .group_by(ReferenciaAgua.especie_id)
        .all()
    )
    return prod, agua


def _to_out(row: Especie, n_prod: int, n_agua: int) -> EspecieCatalogoOut:
    return EspecieCatalogoOut(
        id=row.id,
        nombre_comun=row.nombre_comun,
        nombre_cientifico=row.nombre_cientifico,
        activo=row.activo,
        n_referencias_produccion=n_prod,
        n_referencias_agua=n_agua,
    )


def listar_especies(db: Session, solo_activos: bool = False) -> list[EspecieCatalogoOut]:
    q = db.query(Especie)
    if solo_activos:
        q = q.filter(Especie.activo.is_(True))
    filas = q.order_by(Especie.nombre_comun.asc()).all()
    prod, agua = _conteos(db)
    return [_to_out(row, prod.get(row.id, 0), agua.get(row.id, 0)) for row in filas]


def obtener_especie(db: Session, especie_id: int) -> EspecieCatalogoOut:
    row = db.query(Especie).filter(Especie.id == especie_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Especie no encontrada")
    prod, agua = _conteos(db)
    return _to_out(row, prod.get(row.id, 0), agua.get(row.id, 0))


def _obtener_orm(db: Session, especie_id: int) -> Especie:
    row = db.query(Especie).filter(Especie.id == especie_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Especie no encontrada")
    return row


def crear_especie(db: Session, data: EspecieCreate, usuario_id: int) -> EspecieCatalogoOut:
    existente = db.query(Especie).filter(Especie.nombre_comun == data.nombre_comun).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una especie con el nombre común '{data.nombre_comun}'",
        )

    nuevo = Especie(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una especie con ese nombre común",
        )

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {
            "nombre_comun": nuevo.nombre_comun,
            "nombre_cientifico": nuevo.nombre_cientifico,
            "activo": nuevo.activo,
        },
    )
    db.commit()
    db.refresh(nuevo)
    return _to_out(nuevo, 0, 0)


def actualizar_especie(
    db: Session, especie_id: int, data: EspecieUpdate, usuario_id: int
) -> EspecieCatalogoOut:
    row = _obtener_orm(db, especie_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        prod, agua = _conteos(db)
        return _to_out(row, prod.get(row.id, 0), agua.get(row.id, 0))

    if "nombre_comun" in cambios and cambios["nombre_comun"] != row.nombre_comun:
        existente = (
            db.query(Especie)
            .filter(Especie.nombre_comun == cambios["nombre_comun"], Especie.id != row.id)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe otra especie con el nombre común '{cambios['nombre_comun']}'",
            )

    for key, value in cambios.items():
        setattr(row, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una especie con ese nombre común",
        )

    _registrar_auditoria(db, usuario_id, "UPDATE", row.id, cambios)
    db.commit()
    db.refresh(row)
    prod, agua = _conteos(db)
    return _to_out(row, prod.get(row.id, 0), agua.get(row.id, 0))
