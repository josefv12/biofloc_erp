"""Catálogos mutables de equipo: tipos_equipo y estados_equipo."""
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.equipo import TipoEquipo, EstadoEquipo
from app.models.auditoria import Auditoria
from app.schemas.equipo import (
    TipoEquipoCreate, TipoEquipoUpdate,
    EstadoEquipoCreate, EstadoEquipoUpdate,
)


def _audit(db, usuario_id, tabla, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla=tabla,
                     registro_id=registro_id, accion=accion, detalle=safe))


def _payload_activo(data):
    payload = data.model_dump()
    if payload.get("activo") is None:
        payload["activo"] = True
    return payload


# ── tipos_equipo ─────────────────────────────────────────────────────────────
def listar_tipos_equipo(db: Session, solo_activos: bool = False):
    q = db.query(TipoEquipo)
    if solo_activos:
        q = q.filter(TipoEquipo.activo == True)  # noqa: E712
    return q.order_by(TipoEquipo.nombre.asc()).all()


def obtener_tipo_equipo(db: Session, tipo_id: int) -> TipoEquipo:
    t = db.query(TipoEquipo).filter(TipoEquipo.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo de equipo no encontrado")
    return t


def crear_tipo_equipo(db: Session, data: TipoEquipoCreate, usuario_id: int) -> TipoEquipo:
    if db.query(TipoEquipo).filter(TipoEquipo.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un tipo de equipo con el nombre '{data.nombre}'")
    nuevo = TipoEquipo(**_payload_activo(data))
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando tipo de equipo")
    _audit(db, usuario_id, "tipos_equipo", "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_tipo_equipo(db: Session, tipo_id: int, data: TipoEquipoUpdate, usuario_id: int) -> TipoEquipo:
    t = obtener_tipo_equipo(db, tipo_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return t
    if "nombre" in cambios and cambios["nombre"] != t.nombre:
        if db.query(TipoEquipo).filter(TipoEquipo.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro tipo de equipo con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(t, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando tipo de equipo")
    _audit(db, usuario_id, "tipos_equipo", "UPDATE", t.id, cambios)
    db.commit()
    db.refresh(t)
    return t


# ── estados_equipo ───────────────────────────────────────────────────────────
def listar_estados_equipo(db: Session, solo_activos: bool = False):
    q = db.query(EstadoEquipo)
    if solo_activos:
        q = q.filter(EstadoEquipo.activo == True)  # noqa: E712
    return q.order_by(EstadoEquipo.nombre.asc()).all()


def obtener_estado_equipo(db: Session, estado_id: int) -> EstadoEquipo:
    e = db.query(EstadoEquipo).filter(EstadoEquipo.id == estado_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estado de equipo no encontrado")
    return e


def crear_estado_equipo(db: Session, data: EstadoEquipoCreate, usuario_id: int) -> EstadoEquipo:
    if db.query(EstadoEquipo).filter(EstadoEquipo.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un estado de equipo con el nombre '{data.nombre}'")
    nuevo = EstadoEquipo(**_payload_activo(data))
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando estado de equipo")
    _audit(db, usuario_id, "estados_equipo", "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_estado_equipo(db: Session, estado_id: int, data: EstadoEquipoUpdate, usuario_id: int) -> EstadoEquipo:
    e = obtener_estado_equipo(db, estado_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return e
    if "nombre" in cambios and cambios["nombre"] != e.nombre:
        if db.query(EstadoEquipo).filter(EstadoEquipo.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro estado de equipo con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(e, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando estado de equipo")
    _audit(db, usuario_id, "estados_equipo", "UPDATE", e.id, cambios)
    db.commit()
    db.refresh(e)
    return e
