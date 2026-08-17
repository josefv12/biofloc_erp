"""Catálogo mutable Categorías Gasto."""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.categoria_gasto import CategoriaGasto
from app.models.auditoria import Auditoria
from app.schemas.categoria_gasto import CategoriaGastoCreate, CategoriaGastoUpdate


def _audit(db, usuario_id, accion, registro_id, detalle: dict):
    d = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in detalle.items()}
    db.add(Auditoria(usuario_id=usuario_id, tabla="categorias_gasto",
                     registro_id=registro_id, accion=accion, detalle=d))


def listar_categorias_gasto(db: Session, solo_activos: bool = False):
    q = db.query(CategoriaGasto)
    if solo_activos:
        q = q.filter(CategoriaGasto.activo == True)
    return q.order_by(CategoriaGasto.nombre.asc()).all()


def obtener_categoria_gasto(db: Session, categoria_id: int):
    c = db.query(CategoriaGasto).filter(CategoriaGasto.id == categoria_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoría de gasto no encontrada")
    return c


def crear_categoria_gasto(db: Session, data: CategoriaGastoCreate, usuario_id: int):
    existente = db.query(CategoriaGasto).filter(CategoriaGasto.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Ya existe una categoría de gasto con el nombre '{data.nombre}'")
    payload = data.model_dump()
    if payload.get("activo") is None:
        payload["activo"] = True
    nuevo = CategoriaGasto(**payload)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad creando categoría de gasto")
    _audit(db, usuario_id, "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_categoria_gasto(db: Session, categoria_id: int, data: CategoriaGastoUpdate, usuario_id: int):
    c = obtener_categoria_gasto(db, categoria_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return c
    if "nombre" in cambios and cambios["nombre"] != c.nombre:
        existente = db.query(CategoriaGasto).filter(CategoriaGasto.nombre == cambios["nombre"]).first()
        if existente:
            raise HTTPException(status_code=409, detail=f"Ya existe otra categoría de gasto con nombre '{cambios['nombre']}'")
    for k, v in cambios.items():
        setattr(c, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad actualizando categoría de gasto")
    _audit(db, usuario_id, "UPDATE", c.id, cambios)
    db.commit()
    db.refresh(c)
    return c
