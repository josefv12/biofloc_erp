"""Eventos de energía. POST abre/registra; PUT cierra o actualiza fin/respaldo.

No hay estanque_id en el DDL. No se generan filas en alarmas (fase posterior).
"""
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.evento_energia import EventoEnergia
from app.models.equipo import Equipo
from app.models.auditoria import Auditoria
from app.schemas.evento_energia import EventoEnergiaCreate, EventoEnergiaUpdate


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla="eventos_energia",
                     registro_id=registro_id, accion=accion, detalle=safe))


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _duracion_minutos(inicio: datetime, fin: Optional[datetime]) -> Optional[int]:
    if fin is None:
        return None
    mins = int((_aware(fin) - _aware(inicio)).total_seconds() // 60)
    if mins < 0:
        raise HTTPException(status_code=422, detail="fecha_hora_fin debe ser >= fecha_hora_inicio")
    return mins


def _validar_respaldo(respaldo_activado: bool, equipo_respaldo_id: Optional[int], db: Session):
    if respaldo_activado and equipo_respaldo_id is None:
        raise HTTPException(
            status_code=422,
            detail="equipo_respaldo_id es obligatorio cuando respaldo_activado=true",
        )
    if equipo_respaldo_id is not None:
        if not db.query(Equipo).filter(Equipo.id == equipo_respaldo_id).first():
            raise HTTPException(status_code=404, detail=f"Equipo de respaldo {equipo_respaldo_id} no existe")


def listar_eventos_energia(db: Session,
                           tipo: Optional[str] = None,
                           fecha_desde: Optional[datetime] = None,
                           fecha_hasta: Optional[datetime] = None,
                           respaldo_activado: Optional[bool] = None,
                           equipo_respaldo_id: Optional[int] = None,
                           registrado_por: Optional[int] = None):
    q = db.query(EventoEnergia)
    if tipo:
        q = q.filter(EventoEnergia.tipo.ilike(f"%{tipo}%"))
    if fecha_desde:
        q = q.filter(EventoEnergia.fecha_hora_inicio >= fecha_desde)
    if fecha_hasta:
        q = q.filter(EventoEnergia.fecha_hora_inicio <= fecha_hasta)
    if respaldo_activado is not None:
        q = q.filter(EventoEnergia.respaldo_activado == respaldo_activado)
    if equipo_respaldo_id is not None:
        q = q.filter(EventoEnergia.equipo_respaldo_id == equipo_respaldo_id)
    if registrado_por is not None:
        q = q.filter(EventoEnergia.registrado_por == registrado_por)
    return q.order_by(EventoEnergia.fecha_hora_inicio.desc(), EventoEnergia.id.desc()).all()


def obtener_evento_energia(db: Session, evento_id: int) -> EventoEnergia:
    e = db.query(EventoEnergia).filter(EventoEnergia.id == evento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evento de energía no encontrado")
    return e


def crear_evento_energia(db: Session, data: EventoEnergiaCreate, usuario_id: int) -> EventoEnergia:
    respaldo = bool(data.respaldo_activado)
    _validar_respaldo(respaldo, data.equipo_respaldo_id, db)
    if data.fecha_hora_fin is not None and _aware(data.fecha_hora_fin) < _aware(data.fecha_hora_inicio):
        raise HTTPException(status_code=422, detail="fecha_hora_fin debe ser >= fecha_hora_inicio")
    duracion = data.duracion_minutos
    if data.fecha_hora_fin is not None:
        duracion = _duracion_minutos(data.fecha_hora_inicio, data.fecha_hora_fin)
    tipo = (data.tipo or "CORTE").strip() or "CORTE"
    try:
        nuevo = EventoEnergia(
            fecha_hora_inicio=data.fecha_hora_inicio,
            fecha_hora_fin=data.fecha_hora_fin,
            duracion_minutos=duracion,
            tipo=tipo,
            respaldo_activado=respaldo,
            equipo_respaldo_id=data.equipo_respaldo_id,
            observaciones=data.observaciones.strip() if data.observaciones else None,
            registrado_por=usuario_id,
        )
        db.add(nuevo)
        db.flush()
        _audit(db, usuario_id, "INSERT", nuevo.id, {
            "fecha_hora_inicio": nuevo.fecha_hora_inicio,
            "fecha_hora_fin": nuevo.fecha_hora_fin,
            "duracion_minutos": nuevo.duracion_minutos,
            "tipo": nuevo.tipo,
            "respaldo_activado": nuevo.respaldo_activado,
            "equipo_respaldo_id": nuevo.equipo_respaldo_id,
            "observaciones": nuevo.observaciones,
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad creando evento de energía: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando evento de energía: {e}")
    db.refresh(nuevo)
    return nuevo


def actualizar_evento_energia(db: Session, evento_id: int, data: EventoEnergiaUpdate, usuario_id: int) -> EventoEnergia:
    e = obtener_evento_energia(db, evento_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return e
    respaldo = cambios.get("respaldo_activado", e.respaldo_activado)
    equipo_id = cambios.get("equipo_respaldo_id", e.equipo_respaldo_id)
    _validar_respaldo(bool(respaldo), equipo_id, db)
    fin = cambios.get("fecha_hora_fin", e.fecha_hora_fin)
    if fin is not None and _aware(fin) < _aware(e.fecha_hora_inicio):
        raise HTTPException(status_code=422, detail="fecha_hora_fin debe ser >= fecha_hora_inicio")
    if "fecha_hora_fin" in cambios:
        cambios["duracion_minutos"] = _duracion_minutos(e.fecha_hora_inicio, cambios["fecha_hora_fin"])
    elif "duracion_minutos" in cambios and cambios["duracion_minutos"] is not None and cambios["duracion_minutos"] < 0:
        raise HTTPException(status_code=422, detail="duracion_minutos debe ser >= 0")
    if "tipo" in cambios and cambios["tipo"] is not None:
        cambios["tipo"] = cambios["tipo"].strip() or e.tipo
    if "observaciones" in cambios and cambios["observaciones"] is not None:
        cambios["observaciones"] = cambios["observaciones"].strip() or None
    try:
        for k, v in cambios.items():
            setattr(e, k, v)
        db.flush()
        _audit(db, usuario_id, "UPDATE", e.id, cambios)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad actualizando evento de energía: {err}")
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando evento de energía: {err}")
    db.refresh(e)
    return e
