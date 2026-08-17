"""Sistema general de alarmas (tipos/niveles/estados + alarmas).

No confundir con /api/v1/alertas/stock-bajo (inventario, vista_stock_productos).
No hay triggers que generen filas. No hay FK a fallas ni estanque_id.
Estados reales del DDL: PENDIENTE, ATENDIDA, CERRADA.
"""
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.alarma import Alarma, TipoAlarma, NivelAlarma, EstadoAlarma
from app.models.lote import Lote
from app.models.equipo import Equipo
from app.models.evento_energia import EventoEnergia
from app.models.auditoria import Auditoria
from app.schemas.alarma_sistema import AlarmaCreate, AlarmaUpdate

ESTADOS_ATENCION = {"ATENDIDA", "CERRADA"}
ESTADO_PENDIENTE = "PENDIENTE"


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla="alarmas",
                     registro_id=registro_id, accion=accion, detalle=safe))


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _estado_por_nombre(db: Session, nombre: str) -> EstadoAlarma:
    e = db.query(EstadoAlarma).filter(EstadoAlarma.nombre == nombre).first()
    if not e:
        raise HTTPException(status_code=500, detail=f"Estado de alarma semilla '{nombre}' no encontrado")
    return e


def _nombre_estado(db: Session, estado_id: int) -> str:
    e = db.query(EstadoAlarma).filter(EstadoAlarma.id == estado_id).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Estado de alarma {estado_id} no existe")
    return e.nombre


def _validar_fks(db: Session, tipo_alarma_id: Optional[int], nivel_alarma_id: Optional[int],
                 estado_alarma_id: Optional[int], lote_id: Optional[int],
                 equipo_id: Optional[int], evento_energia_id: Optional[int]):
    if tipo_alarma_id is not None:
        if not db.query(TipoAlarma).filter(TipoAlarma.id == tipo_alarma_id).first():
            raise HTTPException(status_code=404, detail=f"Tipo de alarma {tipo_alarma_id} no existe")
    if nivel_alarma_id is not None:
        if not db.query(NivelAlarma).filter(NivelAlarma.id == nivel_alarma_id).first():
            raise HTTPException(status_code=404, detail=f"Nivel de alarma {nivel_alarma_id} no existe")
    if estado_alarma_id is not None:
        if not db.query(EstadoAlarma).filter(EstadoAlarma.id == estado_alarma_id).first():
            raise HTTPException(status_code=404, detail=f"Estado de alarma {estado_alarma_id} no existe")
    if lote_id is not None:
        if not db.query(Lote).filter(Lote.id == lote_id).first():
            raise HTTPException(status_code=404, detail=f"Lote {lote_id} no existe")
    if equipo_id is not None:
        if not db.query(Equipo).filter(Equipo.id == equipo_id).first():
            raise HTTPException(status_code=404, detail=f"Equipo {equipo_id} no existe")
    if evento_energia_id is not None:
        if not db.query(EventoEnergia).filter(EventoEnergia.id == evento_energia_id).first():
            raise HTTPException(status_code=404, detail=f"Evento de energía {evento_energia_id} no existe")


def _aplicar_atencion(alarma: Alarma, estado_nombre: str, usuario_id: int):
    if estado_nombre not in ESTADOS_ATENCION:
        return
    now = datetime.now(timezone.utc)
    if alarma.atendida_por is None:
        alarma.atendida_por = usuario_id
    if alarma.fecha_atencion is None:
        alarma.fecha_atencion = now
    if alarma.fecha_hora is not None and _aware(alarma.fecha_atencion) < _aware(alarma.fecha_hora):
        raise HTTPException(
            status_code=422,
            detail="fecha_atencion debe ser >= fecha_hora",
        )


def _query_base(db: Session):
    return db.query(Alarma).options(
        joinedload(Alarma.tipo),
        joinedload(Alarma.nivel),
        joinedload(Alarma.estado),
    )


def listar_alarmas(db: Session,
                   tipo_alarma_id: Optional[int] = None,
                   nivel_alarma_id: Optional[int] = None,
                   estado_alarma_id: Optional[int] = None,
                   lote_id: Optional[int] = None,
                   equipo_id: Optional[int] = None,
                   evento_energia_id: Optional[int] = None,
                   fecha_desde: Optional[datetime] = None,
                   fecha_hasta: Optional[datetime] = None):
    q = _query_base(db)
    if tipo_alarma_id is not None:
        q = q.filter(Alarma.tipo_alarma_id == tipo_alarma_id)
    if nivel_alarma_id is not None:
        q = q.filter(Alarma.nivel_alarma_id == nivel_alarma_id)
    if estado_alarma_id is not None:
        q = q.filter(Alarma.estado_alarma_id == estado_alarma_id)
    if lote_id is not None:
        q = q.filter(Alarma.lote_id == lote_id)
    if equipo_id is not None:
        q = q.filter(Alarma.equipo_id == equipo_id)
    if evento_energia_id is not None:
        q = q.filter(Alarma.evento_energia_id == evento_energia_id)
    if fecha_desde:
        q = q.filter(Alarma.fecha_hora >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Alarma.fecha_hora <= fecha_hasta)
    return q.order_by(Alarma.fecha_hora.desc(), Alarma.id.desc()).all()


def obtener_alarma(db: Session, alarma_id: int) -> Alarma:
    a = _query_base(db).filter(Alarma.id == alarma_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    return a


def crear_alarma(db: Session, data: AlarmaCreate, usuario_id: int) -> Alarma:
    titulo = (data.titulo or "").strip()
    mensaje = (data.mensaje or "").strip()
    if not titulo:
        raise HTTPException(status_code=422, detail="título requerido")
    if not mensaje:
        raise HTTPException(status_code=422, detail="mensaje requerido")

    estado_id = data.estado_alarma_id
    if estado_id is None:
        estado_id = _estado_por_nombre(db, ESTADO_PENDIENTE).id

    _validar_fks(
        db,
        tipo_alarma_id=data.tipo_alarma_id,
        nivel_alarma_id=data.nivel_alarma_id,
        estado_alarma_id=estado_id,
        lote_id=data.lote_id,
        equipo_id=data.equipo_id,
        evento_energia_id=data.evento_energia_id,
    )

    try:
        nuevo = Alarma(
            tipo_alarma_id=data.tipo_alarma_id,
            nivel_alarma_id=data.nivel_alarma_id,
            estado_alarma_id=estado_id,
            lote_id=data.lote_id,
            equipo_id=data.equipo_id,
            evento_energia_id=data.evento_energia_id,
            titulo=titulo,
            mensaje=mensaje,
            observaciones=data.observaciones.strip() if data.observaciones else None,
            fecha_hora=data.fecha_hora if data.fecha_hora is not None else datetime.now(timezone.utc),
        )
        db.add(nuevo)
        db.flush()
        estado_nombre = _nombre_estado(db, estado_id)
        _aplicar_atencion(nuevo, estado_nombre, usuario_id)
        db.flush()
        _audit(db, usuario_id, "INSERT", nuevo.id, {
            "tipo_alarma_id": nuevo.tipo_alarma_id,
            "nivel_alarma_id": nuevo.nivel_alarma_id,
            "estado_alarma_id": nuevo.estado_alarma_id,
            "lote_id": nuevo.lote_id,
            "equipo_id": nuevo.equipo_id,
            "evento_energia_id": nuevo.evento_energia_id,
            "fecha_hora": nuevo.fecha_hora,
            "titulo": nuevo.titulo,
            "mensaje": nuevo.mensaje,
            "atendida_por": nuevo.atendida_por,
            "fecha_atencion": nuevo.fecha_atencion,
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "alarmas_check" in msg or "fecha_atencion" in msg:
            raise HTTPException(status_code=422, detail="fecha_atencion debe ser >= fecha_hora")
        raise HTTPException(status_code=400, detail=f"Error de integridad creando alarma: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando alarma: {e}")
    return obtener_alarma(db, nuevo.id)


def actualizar_alarma(db: Session, alarma_id: int, data: AlarmaUpdate, usuario_id: int) -> Alarma:
    a = obtener_alarma(db, alarma_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return a
    if "observaciones" in cambios and cambios["observaciones"] is not None:
        cambios["observaciones"] = cambios["observaciones"].strip() or None
    try:
        if "estado_alarma_id" in cambios and cambios["estado_alarma_id"] is not None:
            _validar_fks(db, None, None, cambios["estado_alarma_id"], None, None, None)
            a.estado_alarma_id = cambios["estado_alarma_id"]
            estado_nombre = _nombre_estado(db, a.estado_alarma_id)
            _aplicar_atencion(a, estado_nombre, usuario_id)
        if "observaciones" in cambios:
            a.observaciones = cambios["observaciones"]
        db.flush()
        audit_detalle = dict(cambios)
        if a.atendida_por is not None:
            audit_detalle["atendida_por"] = a.atendida_por
        if a.fecha_atencion is not None:
            audit_detalle["fecha_atencion"] = a.fecha_atencion
        _audit(db, usuario_id, "UPDATE", a.id, audit_detalle)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "alarmas_check" in msg or "fecha_atencion" in msg:
            raise HTTPException(status_code=422, detail="fecha_atencion debe ser >= fecha_hora")
        raise HTTPException(status_code=400, detail=f"Error de integridad actualizando alarma: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando alarma: {e}")
    return obtener_alarma(db, a.id)
