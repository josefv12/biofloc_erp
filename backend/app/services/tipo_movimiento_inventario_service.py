"""Servicio para el catálogo cerrado de movimientos de inventario."""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.tipo_movimiento_inventario import TipoMovimientoInventario
from app.models.auditoria import Auditoria
from app.schemas.tipo_movimiento_inventario import TipoMovimientoInventarioCreate, TipoMovimientoInventarioUpdate


EFECTOS_FIJOS = {"ENTRADA": 1, "SALIDA": -1, "AJUSTE": 1}


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in detalle.items()}
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="tipos_movimiento_inventario",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    ))


def _validar_tipo(nombre: str, afecta_stock: int):
    if nombre not in EFECTOS_FIJOS:
        raise HTTPException(status_code=422, detail="Tipo de movimiento no permitido. Use ENTRADA, SALIDA o AJUSTE")
    if nombre == "ENTRADA" and afecta_stock != 1:
        raise HTTPException(status_code=422, detail="ENTRADA debe afectar stock con +1")
    if nombre == "SALIDA" and afecta_stock != -1:
        raise HTTPException(status_code=422, detail="SALIDA debe afectar stock con -1")
    if nombre == "AJUSTE" and afecta_stock != 1:
        raise HTTPException(status_code=422, detail="AJUSTE usa +1 como valor base; el sentido real se define en el movimiento")


def listar_tipos_movimiento_inventario(db: Session) -> list[TipoMovimientoInventario]:
    return db.query(TipoMovimientoInventario).order_by(TipoMovimientoInventario.id.asc()).all()


def obtener_tipo_movimiento_inventario(db: Session, tipo_id: int) -> TipoMovimientoInventario:
    t = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo de movimiento de inventario no encontrado")
    return t


def crear_tipo_movimiento_inventario(db: Session, data: TipoMovimientoInventarioCreate, usuario_id: int) -> TipoMovimientoInventario:
    existente = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Ya existe un tipo de movimiento con nombre '{data.nombre}'")

    _validar_tipo(data.nombre, data.afecta_stock)
    nuevo = TipoMovimientoInventario(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar el tipo de movimiento")

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {
        "nombre": nuevo.nombre, "afecta_stock": nuevo.afecta_stock
    })
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_tipo_movimiento_inventario(db: Session, tipo_id: int, data: TipoMovimientoInventarioUpdate, usuario_id: int) -> TipoMovimientoInventario:
    t = obtener_tipo_movimiento_inventario(db, tipo_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return t

    nombre_final = cambios.get("nombre", t.nombre)
    efecto_final = cambios.get("afecta_stock", t.afecta_stock)
    _validar_tipo(nombre_final, efecto_final)

    if "nombre" in cambios and cambios["nombre"] != t.nombre:
        if db.query(TipoMovimientoInventario).filter(
            TipoMovimientoInventario.nombre == cambios["nombre"],
            TipoMovimientoInventario.id != tipo_id,
        ).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro tipo de movimiento con nombre '{cambios['nombre']}'")

    for key, value in cambios.items():
        setattr(t, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar tipo de movimiento")

    _registrar_auditoria(db, usuario_id, "UPDATE", t.id, cambios)
    db.commit()
    db.refresh(t)
    return t
