"""
Servicio para catálogo productos + consulta de stock mediante vista_stock_productos.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from fastapi import HTTPException

from app.models.producto import Producto
from app.models.unidad import Unidad
from app.models.categoria_inventario import CategoriaInventario
from app.models.auditoria import Auditoria
from app.schemas.producto import ProductoCreate, ProductoUpdate, StockProductoOut


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            detalle_safe[k] = float(v)
        else:
            detalle_safe[k] = v
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="productos",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    )
    db.add(entrada)


def _verificar_referencias(db: Session, categoria_id: int | None, unidad_id: int | None):
    if categoria_id is not None:
        if not db.query(CategoriaInventario).filter(CategoriaInventario.id == categoria_id, CategoriaInventario.activo == True).first():
            raise HTTPException(status_code=404, detail=f"Categoría id={categoria_id} inexistente o inactiva")
    if unidad_id is not None:
        if not db.query(Unidad).filter(Unidad.id == unidad_id, Unidad.activo == True).first():
            raise HTTPException(status_code=404, detail=f"Unidad id={unidad_id} inexistente o inactiva")


def listar_productos(db: Session, solo_activos: bool = False, categoria_id: int | None = None) -> list[Producto]:
    q = db.query(Producto)
    if solo_activos:
        q = q.filter(Producto.activo == True)
    if categoria_id:
        q = q.filter(Producto.categoria_id == categoria_id)
    return q.order_by(Producto.codigo.asc()).all()


def obtener_producto(db: Session, producto_id: int) -> Producto:
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return p


def crear_producto(db: Session, data: ProductoCreate, usuario_id: int) -> Producto:
    _verificar_referencias(db, data.categoria_id, data.unidad_id)

    ex_codigo = db.query(Producto).filter(Producto.codigo == data.codigo).first()
    if ex_codigo:
        raise HTTPException(status_code=409, detail=f"Ya existe un producto con el código '{data.codigo}'")

    nuevo = Producto(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad al crear producto: {str(e)}")

    _registrar_auditoria(
        db, usuario_id, "INSERT", nuevo.id,
        {"codigo": nuevo.codigo, "nombre": nuevo.nombre, "categoria_id": nuevo.categoria_id,
         "unidad_id": nuevo.unidad_id, "stock_minimo": nuevo.stock_minimo, "activo": nuevo.activo}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_producto(db: Session, producto_id: int, data: ProductoUpdate, usuario_id: int) -> Producto:
    p = obtener_producto(db, producto_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return p

    _verificar_referencias(db, cambios.get("categoria_id"), cambios.get("unidad_id"))

    if "codigo" in cambios and cambios["codigo"] != p.codigo:
        if db.query(Producto).filter(Producto.codigo == cambios["codigo"], Producto.id != producto_id).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otro producto con código '{cambios['codigo']}'")

    for key, value in cambios.items():
        setattr(p, key, value)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad al actualizar producto: {str(e)}")

    _registrar_auditoria(db, usuario_id, "UPDATE", p.id, cambios)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# STOCK vía vista_stock_productos (siempre desde PostgreSQL — no Python)
# ---------------------------------------------------------------------------

def obtener_stock_producto(db: Session, producto_id: int) -> StockProductoOut:
    obtener_producto(db, producto_id)  # 404 si no existe
    row = db.execute(text("""
        SELECT producto_id, codigo, nombre, unidad, stock_actual, stock_minimo
        FROM biofloc.vista_stock_productos
        WHERE producto_id = :pid
    """), {"pid": producto_id}).mappings().first()
    if not row:
        return StockProductoOut(
            producto_id=producto_id,
            codigo="", nombre="", unidad="",
            stock_actual=Decimal("0"), stock_minimo=Decimal("0"),
        )
    return StockProductoOut(**row)


def listar_stock_productos(db: Session) -> list[StockProductoOut]:
    rows = db.execute(text("""
        SELECT producto_id, codigo, nombre, unidad, stock_actual, stock_minimo
        FROM biofloc.vista_stock_productos
        ORDER BY codigo ASC
    """)).mappings().all()
    return [StockProductoOut(**r) for r in rows]
