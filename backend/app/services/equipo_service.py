"""Equipos MUTABLES (GET/POST/PUT). updated_at lo mantiene el trigger PostgreSQL."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.equipo import Equipo, TipoEquipo, EstadoEquipo
from app.models.auditoria import Auditoria
from app.schemas.equipo import EquipoCreate, EquipoUpdate


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla="equipos",
                     registro_id=registro_id, accion=accion, detalle=safe))


def _strip(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def listar_equipos(db: Session,
                   solo_activos: bool = False,
                   tipo_equipo_id: Optional[int] = None,
                   estado_id: Optional[int] = None,
                   codigo: Optional[str] = None,
                   nombre: Optional[str] = None):
    q = db.query(Equipo).options(joinedload(Equipo.tipo), joinedload(Equipo.estado))
    if solo_activos:
        q = q.filter(Equipo.activo == True)  # noqa: E712
    if tipo_equipo_id is not None:
        q = q.filter(Equipo.tipo_equipo_id == tipo_equipo_id)
    if estado_id is not None:
        q = q.filter(Equipo.estado_id == estado_id)
    if codigo:
        q = q.filter(Equipo.codigo.ilike(f"%{codigo}%"))
    if nombre:
        q = q.filter(Equipo.nombre.ilike(f"%{nombre}%"))
    return q.order_by(Equipo.codigo.asc()).all()


def obtener_equipo(db: Session, equipo_id: int) -> Equipo:
    e = db.query(Equipo).options(joinedload(Equipo.tipo), joinedload(Equipo.estado)).filter(Equipo.id == equipo_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return e


def _validar_fks(db: Session, tipo_equipo_id: Optional[int], estado_id: Optional[int]):
    if tipo_equipo_id is not None:
        t = db.query(TipoEquipo).filter(TipoEquipo.id == tipo_equipo_id).first()
        if not t:
            raise HTTPException(status_code=404, detail=f"Tipo de equipo {tipo_equipo_id} no existe")
    if estado_id is not None:
        e = db.query(EstadoEquipo).filter(EstadoEquipo.id == estado_id).first()
        if not e:
            raise HTTPException(status_code=404, detail=f"Estado de equipo {estado_id} no existe")


def crear_equipo(db: Session, data: EquipoCreate, usuario_id: int) -> Equipo:
    _validar_fks(db, data.tipo_equipo_id, data.estado_id)
    codigo = data.codigo.strip()
    if db.query(Equipo).filter(Equipo.codigo == codigo).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un equipo con el código '{codigo}'")
    valor = None
    if data.valor_adquisicion is not None:
        valor = Decimal(data.valor_adquisicion).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if valor < 0:
            raise HTTPException(status_code=422, detail="valor_adquisicion debe ser >= 0")
    payload = data.model_dump()
    payload["codigo"] = codigo
    payload["nombre"] = data.nombre.strip()
    payload["marca"] = _strip(data.marca)
    payload["modelo"] = _strip(data.modelo)
    payload["numero_serie"] = _strip(data.numero_serie)
    payload["ubicacion"] = _strip(data.ubicacion)
    payload["observaciones"] = _strip(data.observaciones)
    payload["valor_adquisicion"] = valor
    if payload.get("activo") is None:
        payload["activo"] = True
    try:
        nuevo = Equipo(**payload)
        db.add(nuevo)
        db.flush()
        _audit(db, usuario_id, "INSERT", nuevo.id, {
            "codigo": nuevo.codigo,
            "nombre": nuevo.nombre,
            "tipo_equipo_id": nuevo.tipo_equipo_id,
            "estado_id": nuevo.estado_id,
            "valor_adquisicion": Decimal(nuevo.valor_adquisicion) if nuevo.valor_adquisicion is not None else None,
            "activo": nuevo.activo,
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad creando equipo: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando equipo: {e}")
    return obtener_equipo(db, nuevo.id)


def actualizar_equipo(db: Session, equipo_id: int, data: EquipoUpdate, usuario_id: int) -> Equipo:
    e = obtener_equipo(db, equipo_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return e
    _validar_fks(db, cambios.get("tipo_equipo_id"), cambios.get("estado_id"))
    if "codigo" in cambios:
        codigo = cambios["codigo"].strip()
        if db.query(Equipo).filter(Equipo.codigo == codigo, Equipo.id != e.id).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro equipo con el código '{codigo}'")
        cambios["codigo"] = codigo
    if "nombre" in cambios:
        cambios["nombre"] = cambios["nombre"].strip()
    if "valor_adquisicion" in cambios and cambios["valor_adquisicion"] is not None:
        cambios["valor_adquisicion"] = Decimal(cambios["valor_adquisicion"]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    for campo in ("marca", "modelo", "numero_serie", "ubicacion", "observaciones"):
        if campo in cambios:
            cambios[campo] = _strip(cambios[campo])
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
        raise HTTPException(status_code=400, detail=f"Error de integridad actualizando equipo: {err}")
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando equipo: {err}")
    return obtener_equipo(db, e.id)
