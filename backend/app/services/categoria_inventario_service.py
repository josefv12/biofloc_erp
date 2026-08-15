"""
Servicio para operaciones CRUD del catálogo categorias_inventario.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.categoria_inventario import CategoriaInventario
from app.models.auditoria import Auditoria
from app.schemas.categoria_inventario import CategoriaInventarioCreate, CategoriaInventarioUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in detalle.items()}
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="categorias_inventario",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    )
    db.add(entrada)


def listar_categorias_inventario(db: Session, solo_activos: bool = False) -> list[CategoriaInventario]:
    q = db.query(CategoriaInventario)
    if solo_activos:
        q = q.filter(CategoriaInventario.activo == True)
    return q.order_by(CategoriaInventario.nombre.asc()).all()


def obtener_categoria_inventario(db: Session, categoria_id: int) -> CategoriaInventario:
    c = db.query(CategoriaInventario).filter(CategoriaInventario.id == categoria_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoría de inventario no encontrada")
    return c


def crear_categoria_inventario(db: Session, data: CategoriaInventarioCreate, usuario_id: int) -> CategoriaInventario:
    existente = db.query(CategoriaInventario).filter(CategoriaInventario.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Ya existe una categoría con el nombre '{data.nombre}'")

    nuevo = CategoriaInventario(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar la categoría")

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {"nombre": nuevo.nombre, "activo": nuevo.activo})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_categoria_inventario(db: Session, categoria_id: int, data: CategoriaInventarioUpdate, usuario_id: int) -> CategoriaInventario:
    c = obtener_categoria_inventario(db, categoria_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return c

    if "nombre" in cambios and cambios["nombre"] != c.nombre:
        existente = db.query(CategoriaInventario).filter(CategoriaInventario.nombre == cambios["nombre"]).first()
        if existente:
            raise HTTPException(status_code=409, detail=f"Ya existe otra categoría con el nombre '{cambios['nombre']}'")

    for key, value in cambios.items():
        setattr(c, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar la categoría")

    _registrar_auditoria(db, usuario_id, "UPDATE", c.id, cambios)
    db.commit()
    db.refresh(c)
    return c
