"""Fallas de equipo. POST inmutable en FKs; PUT limitado a solución/impacto/costo/descripcion."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.falla import Falla
from app.models.equipo import Equipo
from app.models.auditoria import Auditoria
from app.schemas.falla import FallaCreate, FallaUpdate


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla="fallas",
                     registro_id=registro_id, accion=accion, detalle=safe))


def listar_fallas(db: Session,
                  equipo_id: Optional[int] = None,
                  fecha_desde: Optional[datetime] = None,
                  fecha_hasta: Optional[datetime] = None,
                  registrada_por: Optional[int] = None):
    q = db.query(Falla)
    if equipo_id is not None:
        q = q.filter(Falla.equipo_id == equipo_id)
    if fecha_desde:
        q = q.filter(Falla.fecha_hora >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Falla.fecha_hora <= fecha_hasta)
    if registrada_por is not None:
        q = q.filter(Falla.registrada_por == registrada_por)
    return q.order_by(Falla.fecha_hora.desc(), Falla.id.desc()).all()


def obtener_falla(db: Session, falla_id: int) -> Falla:
    f = db.query(Falla).filter(Falla.id == falla_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Falla no encontrada")
    return f


def crear_falla(db: Session, data: FallaCreate, usuario_id: int) -> Falla:
    if not db.query(Equipo).filter(Equipo.id == data.equipo_id).first():
        raise HTTPException(status_code=404, detail=f"Equipo {data.equipo_id} no existe")
    if not data.descripcion or not data.descripcion.strip():
        raise HTTPException(status_code=422, detail="descripción requerida")
    costo = Decimal(data.costo if data.costo is not None else 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if costo < 0:
        raise HTTPException(status_code=422, detail="costo debe ser >= 0")
    try:
        nuevo = Falla(
            equipo_id=data.equipo_id,
            fecha_hora=data.fecha_hora,
            descripcion=data.descripcion.strip(),
            impacto=data.impacto.strip() if data.impacto else None,
            solucion=data.solucion.strip() if data.solucion else None,
            costo=costo,
            registrada_por=usuario_id,
        )
        db.add(nuevo)
        db.flush()
        _audit(db, usuario_id, "INSERT", nuevo.id, {
            "equipo_id": nuevo.equipo_id,
            "fecha_hora": nuevo.fecha_hora,
            "descripcion": nuevo.descripcion,
            "impacto": nuevo.impacto,
            "solucion": nuevo.solucion,
            "costo": Decimal(nuevo.costo),
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad creando falla: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando falla: {e}")
    db.refresh(nuevo)
    return nuevo


def actualizar_falla(db: Session, falla_id: int, data: FallaUpdate, usuario_id: int) -> Falla:
    f = obtener_falla(db, falla_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return f
    if "descripcion" in cambios:
        if not cambios["descripcion"] or not str(cambios["descripcion"]).strip():
            raise HTTPException(status_code=422, detail="descripción requerida")
        cambios["descripcion"] = cambios["descripcion"].strip()
    if "impacto" in cambios and cambios["impacto"] is not None:
        cambios["impacto"] = cambios["impacto"].strip() or None
    if "solucion" in cambios and cambios["solucion"] is not None:
        cambios["solucion"] = cambios["solucion"].strip() or None
    if "costo" in cambios and cambios["costo"] is not None:
        cambios["costo"] = Decimal(cambios["costo"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if cambios["costo"] < 0:
            raise HTTPException(status_code=422, detail="costo debe ser >= 0")
    try:
        for k, v in cambios.items():
            setattr(f, k, v)
        db.flush()
        _audit(db, usuario_id, "UPDATE", f.id, cambios)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad actualizando falla: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando falla: {e}")
    db.refresh(f)
    return f
