"""Catálogos mutables: tipos_alarma, niveles_alarma, estados_alarma."""
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.alarma import TipoAlarma, NivelAlarma, EstadoAlarma
from app.models.auditoria import Auditoria
from app.schemas.alarma_sistema import (
    TipoAlarmaCreate, TipoAlarmaUpdate,
    NivelAlarmaCreate, NivelAlarmaUpdate,
    EstadoAlarmaCreate, EstadoAlarmaUpdate,
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


# ── tipos_alarma ─────────────────────────────────────────────────────────────
def listar_tipos_alarma(db: Session, solo_activos: bool = False):
    q = db.query(TipoAlarma)
    if solo_activos:
        q = q.filter(TipoAlarma.activo == True)  # noqa: E712
    return q.order_by(TipoAlarma.nombre.asc()).all()


def obtener_tipo_alarma(db: Session, tipo_id: int) -> TipoAlarma:
    t = db.query(TipoAlarma).filter(TipoAlarma.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo de alarma no encontrado")
    return t


def crear_tipo_alarma(db: Session, data: TipoAlarmaCreate, usuario_id: int) -> TipoAlarma:
    if db.query(TipoAlarma).filter(TipoAlarma.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un tipo de alarma con el nombre '{data.nombre}'")
    nuevo = TipoAlarma(**_payload_activo(data))
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando tipo de alarma")
    _audit(db, usuario_id, "tipos_alarma", "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_tipo_alarma(db: Session, tipo_id: int, data: TipoAlarmaUpdate, usuario_id: int) -> TipoAlarma:
    t = obtener_tipo_alarma(db, tipo_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return t
    if "nombre" in cambios and cambios["nombre"] != t.nombre:
        if db.query(TipoAlarma).filter(TipoAlarma.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro tipo de alarma con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(t, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando tipo de alarma")
    _audit(db, usuario_id, "tipos_alarma", "UPDATE", t.id, cambios)
    db.commit()
    db.refresh(t)
    return t


# ── niveles_alarma ───────────────────────────────────────────────────────────
def listar_niveles_alarma(db: Session):
    return db.query(NivelAlarma).order_by(NivelAlarma.prioridad.asc(), NivelAlarma.nombre.asc()).all()


def obtener_nivel_alarma(db: Session, nivel_id: int) -> NivelAlarma:
    n = db.query(NivelAlarma).filter(NivelAlarma.id == nivel_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nivel de alarma no encontrado")
    return n


def crear_nivel_alarma(db: Session, data: NivelAlarmaCreate, usuario_id: int) -> NivelAlarma:
    if db.query(NivelAlarma).filter(NivelAlarma.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un nivel de alarma con el nombre '{data.nombre}'")
    if data.prioridad <= 0:
        raise HTTPException(status_code=422, detail="prioridad debe ser > 0")
    nuevo = NivelAlarma(nombre=data.nombre, prioridad=data.prioridad)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "prioridad" in msg:
            raise HTTPException(status_code=422, detail="prioridad debe ser > 0")
        raise HTTPException(status_code=400, detail="Error de integridad creando nivel de alarma")
    _audit(db, usuario_id, "niveles_alarma", "INSERT", nuevo.id,
           {"nombre": nuevo.nombre, "prioridad": nuevo.prioridad})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_nivel_alarma(db: Session, nivel_id: int, data: NivelAlarmaUpdate, usuario_id: int) -> NivelAlarma:
    n = obtener_nivel_alarma(db, nivel_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return n
    if "nombre" in cambios and cambios["nombre"] != n.nombre:
        if db.query(NivelAlarma).filter(NivelAlarma.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro nivel de alarma con nombre '{cambios['nombre']}'")
    if "prioridad" in cambios and cambios["prioridad"] is not None and cambios["prioridad"] <= 0:
        raise HTTPException(status_code=422, detail="prioridad debe ser > 0")
    for k, v in cambios.items():
        setattr(n, k, v)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "prioridad" in msg:
            raise HTTPException(status_code=422, detail="prioridad debe ser > 0")
        raise HTTPException(status_code=400, detail="Error de integridad actualizando nivel de alarma")
    _audit(db, usuario_id, "niveles_alarma", "UPDATE", n.id, cambios)
    db.commit()
    db.refresh(n)
    return n


# ── estados_alarma ───────────────────────────────────────────────────────────
def listar_estados_alarma(db: Session):
    return db.query(EstadoAlarma).order_by(EstadoAlarma.id.asc()).all()


def obtener_estado_alarma(db: Session, estado_id: int) -> EstadoAlarma:
    e = db.query(EstadoAlarma).filter(EstadoAlarma.id == estado_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estado de alarma no encontrado")
    return e


def crear_estado_alarma(db: Session, data: EstadoAlarmaCreate, usuario_id: int) -> EstadoAlarma:
    if db.query(EstadoAlarma).filter(EstadoAlarma.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un estado de alarma con el nombre '{data.nombre}'")
    nuevo = EstadoAlarma(nombre=data.nombre, descripcion=data.descripcion)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando estado de alarma")
    _audit(db, usuario_id, "estados_alarma", "INSERT", nuevo.id, {"nombre": nuevo.nombre})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_estado_alarma(db: Session, estado_id: int, data: EstadoAlarmaUpdate, usuario_id: int) -> EstadoAlarma:
    e = obtener_estado_alarma(db, estado_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return e
    if "nombre" in cambios and cambios["nombre"] != e.nombre:
        if db.query(EstadoAlarma).filter(EstadoAlarma.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro estado de alarma con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(e, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando estado de alarma")
    _audit(db, usuario_id, "estados_alarma", "UPDATE", e.id, cambios)
    db.commit()
    db.refresh(e)
    return e
