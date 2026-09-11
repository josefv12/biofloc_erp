"""Gastos INMUTABLES (POST + GET lista + GET detalle). Auditoría INSERT."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.gasto import Gasto
from app.models.auditoria import Auditoria
from app.models.categoria_gasto import CategoriaGasto
from app.models.lote import Lote
from app.models.estanque import Estanque
from app.schemas.gasto import GastoCreate


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla="gastos",
                     registro_id=registro_id, accion=accion, detalle=safe))


def listar_gastos(db: Session,
                  fecha_desde: Optional[date] = None,
                  fecha_hasta: Optional[date] = None,
                  categoria_id: Optional[int] = None,
                  lote_id: Optional[int] = None,
                  estanque_id: Optional[int] = None,
                  proveedor: Optional[str] = None,
                  registrado_por: Optional[int] = None):
    q = db.query(Gasto).options(joinedload(Gasto.categoria), joinedload(Gasto.lote), joinedload(Gasto.estanque))
    if fecha_desde:
        q = q.filter(Gasto.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Gasto.fecha <= fecha_hasta)
    if categoria_id is not None:
        q = q.filter(Gasto.categoria_id == categoria_id)
    if lote_id is not None:
        q = q.filter(Gasto.lote_id == lote_id)
    if estanque_id is not None:
        q = q.filter(Gasto.estanque_id == estanque_id)
    if proveedor:
        q = q.filter(Gasto.proveedor.ilike(f"%{proveedor}%"))
    if registrado_por is not None:
        q = q.filter(Gasto.registrado_por == registrado_por)
    return q.order_by(Gasto.fecha.desc(), Gasto.id.desc()).all()


def obtener_gasto(db: Session, gasto_id: int) -> Gasto:
    g = db.query(Gasto).options(joinedload(Gasto.categoria), joinedload(Gasto.lote), joinedload(Gasto.estanque)).filter(Gasto.id == gasto_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return g


def crear_gasto(db: Session, data: GastoCreate, usuario_id: int) -> Gasto:
    cat = db.query(CategoriaGasto).filter(CategoriaGasto.id == data.categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail=f"Categoría de gasto {data.categoria_id} no existe")
    if data.lote_id is not None:
        lo = db.query(Lote).filter(Lote.id == data.lote_id).first()
        if not lo:
            raise HTTPException(status_code=404, detail=f"Lote {data.lote_id} no existe")
    if data.estanque_id is not None:
        es = db.query(Estanque).filter(Estanque.id == data.estanque_id).first()
        if not es:
            raise HTTPException(status_code=404, detail=f"Estanque {data.estanque_id} no existe")
    if data.lote_id is not None and data.estanque_id is not None:
        raise HTTPException(status_code=422, detail="Un costo debe asociarse a un lote o a un estanque, no a ambos")

    valor = Decimal(data.valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if valor <= 0:
        raise HTTPException(status_code=422, detail="valor debe ser mayor que 0")
    if not data.descripcion or not data.descripcion.strip():
        raise HTTPException(status_code=422, detail="descripción requerida")

    proveedor = data.proveedor.strip() if data.proveedor else None
    observaciones = data.observaciones.strip() if data.observaciones else None

    try:
        nuevo = Gasto(
            fecha=data.fecha,
            categoria_id=data.categoria_id,
            lote_id=data.lote_id,
            estanque_id=data.estanque_id,
            descripcion=data.descripcion.strip(),
            valor=valor,
            proveedor=proveedor,
            observaciones=observaciones,
            registrado_por=usuario_id,
        )
        db.add(nuevo)
        db.flush()
        _audit(db, usuario_id, "INSERT", nuevo.id, {
            "fecha": nuevo.fecha,
            "categoria_id": nuevo.categoria_id,
            "lote_id": nuevo.lote_id,
            "estanque_id": nuevo.estanque_id,
            "descripcion": nuevo.descripcion,
            "valor": Decimal(nuevo.valor),
            "proveedor": nuevo.proveedor,
            "observaciones": nuevo.observaciones,
        })
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No fue posible registrar el gasto por una regla de integridad.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible registrar el gasto por un error interno.")

    db.refresh(nuevo)
    return nuevo
