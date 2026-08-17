"""Tipos de mantenimiento (catálogo mutable) + mantenimientos INMUTABLES."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.mantenimiento import TipoMantenimiento, Mantenimiento
from app.models.equipo import Equipo
from app.models.auditoria import Auditoria
from app.schemas.mantenimiento import TipoMantenimientoCreate, TipoMantenimientoUpdate, MantenimientoCreate


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


def listar_tipos_mantenimiento(db: Session, solo_activos: bool = False):
    q = db.query(TipoMantenimiento)
    if solo_activos:
        q = q.filter(TipoMantenimiento.activo == True)  # noqa: E712
    return q.order_by(TipoMantenimiento.nombre.asc()).all()


def obtener_tipo_mantenimiento(db: Session, tipo_id: int) -> TipoMantenimiento:
    t = db.query(TipoMantenimiento).filter(TipoMantenimiento.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo de mantenimiento no encontrado")
    return t


def crear_tipo_mantenimiento(db: Session, data: TipoMantenimientoCreate, usuario_id: int) -> TipoMantenimiento:
    if db.query(TipoMantenimiento).filter(TipoMantenimiento.nombre == data.nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un tipo de mantenimiento con el nombre '{data.nombre}'")
    payload = data.model_dump()
    if payload.get("activo") is None:
        payload["activo"] = True
    nuevo = TipoMantenimiento(**payload)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando tipo de mantenimiento")
    _audit(db, usuario_id, "tipos_mantenimiento", "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_tipo_mantenimiento(db: Session, tipo_id: int, data: TipoMantenimientoUpdate, usuario_id: int) -> TipoMantenimiento:
    t = obtener_tipo_mantenimiento(db, tipo_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return t
    if "nombre" in cambios and cambios["nombre"] != t.nombre:
        if db.query(TipoMantenimiento).filter(TipoMantenimiento.nombre == cambios["nombre"]).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro tipo de mantenimiento con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(t, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando tipo de mantenimiento")
    _audit(db, usuario_id, "tipos_mantenimiento", "UPDATE", t.id, cambios)
    db.commit()
    db.refresh(t)
    return t


def listar_mantenimientos(db: Session,
                          equipo_id: Optional[int] = None,
                          tipo_mantenimiento_id: Optional[int] = None,
                          fecha_desde: Optional[date] = None,
                          fecha_hasta: Optional[date] = None,
                          registrado_por: Optional[int] = None):
    q = db.query(Mantenimiento)
    if equipo_id is not None:
        q = q.filter(Mantenimiento.equipo_id == equipo_id)
    if tipo_mantenimiento_id is not None:
        q = q.filter(Mantenimiento.tipo_mantenimiento_id == tipo_mantenimiento_id)
    if fecha_desde:
        q = q.filter(Mantenimiento.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Mantenimiento.fecha <= fecha_hasta)
    if registrado_por is not None:
        q = q.filter(Mantenimiento.registrado_por == registrado_por)
    return q.order_by(Mantenimiento.fecha.desc(), Mantenimiento.id.desc()).all()


def obtener_mantenimiento(db: Session, mant_id: int) -> Mantenimiento:
    m = db.query(Mantenimiento).filter(Mantenimiento.id == mant_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")
    return m


def crear_mantenimiento(db: Session, data: MantenimientoCreate, usuario_id: int) -> Mantenimiento:
    if not db.query(Equipo).filter(Equipo.id == data.equipo_id).first():
        raise HTTPException(status_code=404, detail=f"Equipo {data.equipo_id} no existe")
    if not db.query(TipoMantenimiento).filter(TipoMantenimiento.id == data.tipo_mantenimiento_id).first():
        raise HTTPException(status_code=404, detail=f"Tipo de mantenimiento {data.tipo_mantenimiento_id} no existe")
    if not data.descripcion or not data.descripcion.strip():
        raise HTTPException(status_code=422, detail="descripción requerida")
    costo = Decimal(data.costo if data.costo is not None else 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if costo < 0:
        raise HTTPException(status_code=422, detail="costo debe ser >= 0")
    try:
        nuevo = Mantenimiento(
            equipo_id=data.equipo_id,
            tipo_mantenimiento_id=data.tipo_mantenimiento_id,
            fecha=data.fecha,
            descripcion=data.descripcion.strip(),
            costo=costo,
            proveedor=data.proveedor.strip() if data.proveedor else None,
            observaciones=data.observaciones.strip() if data.observaciones else None,
            registrado_por=usuario_id,
        )
        db.add(nuevo)
        db.flush()
        _audit(db, usuario_id, "mantenimientos", "INSERT", nuevo.id, {
            "equipo_id": nuevo.equipo_id,
            "tipo_mantenimiento_id": nuevo.tipo_mantenimiento_id,
            "fecha": nuevo.fecha,
            "descripcion": nuevo.descripcion,
            "costo": Decimal(nuevo.costo),
            "proveedor": nuevo.proveedor,
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad creando mantenimiento: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando mantenimiento: {e}")
    db.refresh(nuevo)
    return nuevo
