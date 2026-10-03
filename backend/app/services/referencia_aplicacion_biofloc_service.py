from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.lote import Especie
from app.models.producto import Producto
from app.models.referencia_aplicacion_biofloc import ReferenciaAplicacionBiofloc
from app.schemas.referencia_aplicacion_biofloc import (
    ReferenciaAplicacionBioflocCreate,
    ReferenciaAplicacionBioflocUpdate,
)


def _auditar(db: Session, usuario_id: int, accion: str, row: ReferenciaAplicacionBiofloc, cambios: dict):
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="referencias_aplicacion_biofloc",
            registro_id=row.id,
            accion=accion,
            detalle=cambios,
        )
    )


def listar(db: Session, especie_id: int | None = None, semana: int | None = None, solo_activos: bool = False):
    q = db.query(ReferenciaAplicacionBiofloc)
    if especie_id:
        q = q.filter(ReferenciaAplicacionBiofloc.especie_id == especie_id)
    if semana:
        q = q.filter(ReferenciaAplicacionBiofloc.semana == semana)
    if solo_activos:
        q = q.filter(ReferenciaAplicacionBiofloc.activo.is_(True))
    return q.order_by(ReferenciaAplicacionBiofloc.especie_id, ReferenciaAplicacionBiofloc.semana, ReferenciaAplicacionBiofloc.id).all()


def obtener(db: Session, referencia_id: int):
    row = db.query(ReferenciaAplicacionBiofloc).filter(ReferenciaAplicacionBiofloc.id == referencia_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Referencia semanal Biofloc no encontrada")
    return row


def crear(db: Session, data: ReferenciaAplicacionBioflocCreate, usuario_id: int):
    if not db.query(Especie).filter(Especie.id == data.especie_id).first():
        raise HTTPException(status_code=404, detail=f"Especie id={data.especie_id} no existe")

    producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto id={data.producto_id} no existe")
    if not producto.activo:
        raise HTTPException(status_code=422, detail="El producto de la referencia está inactivo")

    existente = db.query(ReferenciaAplicacionBiofloc).filter(
        ReferenciaAplicacionBiofloc.especie_id == data.especie_id,
        ReferenciaAplicacionBiofloc.semana == data.semana,
        ReferenciaAplicacionBiofloc.producto_id == data.producto_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ya existe una referencia para esa especie, semana y producto")

    row = ReferenciaAplicacionBiofloc(**data.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad en referencia semanal Biofloc")
    _auditar(db, usuario_id, "INSERT", row, {
        "especie_id": row.especie_id,
        "semana": row.semana,
        "fase": row.fase,
        "producto_id": row.producto_id,
        "cantidad_referencia": float(row.cantidad_referencia),
    })
    db.commit()
    db.refresh(row)
    return row


def actualizar(db: Session, referencia_id: int, data: ReferenciaAplicacionBioflocUpdate, usuario_id: int):
    row = obtener(db, referencia_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return row
    for key, value in cambios.items():
        setattr(row, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad al actualizar referencia semanal Biofloc")
    _auditar(db, usuario_id, "UPDATE", row, {k: float(v) if isinstance(v, Decimal) else v for k, v in cambios.items()})
    db.commit()
    db.refresh(row)
    return row
