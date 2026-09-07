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


def _verificar_referencias(
    db: Session,
    categoria_id: int | None,
    unidad_id: int | None,
    unidad_comercial_id: int | None,
):
    if categoria_id is not None:
        if not db.query(CategoriaInventario).filter(CategoriaInventario.id == categoria_id, CategoriaInventario.activo == True).first():
            raise HTTPException(status_code=404, detail=f"Categoría id={categoria_id} inexistente o inactiva")
    if unidad_id is not None:
        if not db.query(Unidad).filter(Unidad.id == unidad_id, Unidad.activo == True).first():
            raise HTTPException(status_code=404, detail=f"Unidad interna id={unidad_id} inexistente o inactiva")
    if unidad_comercial_id is not None:
        if not db.query(Unidad).filter(Unidad.id == unidad_comercial_id, Unidad.activo == True).first():
            raise HTTPException(status_code=404, detail=f"Unidad comercial id={unidad_comercial_id} inexistente o inactiva")


def _validar_factor(factor_conversion: Decimal):
    if factor_conversion <= 0:
        raise HTTPException(status_code=422, detail="El factor de conversión debe ser mayor que cero")


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
    _verificar_referencias(db, data.categoria_id, data.unidad_id, data.unidad_comercial_id)
    _validar_factor(data.factor_conversion)

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
        {
            "codigo": nuevo.codigo,
            "nombre": nuevo.nombre,
            "categoria_id": nuevo.categoria_id,
            "unidad_id": nuevo.unidad_id,
            "unidad_comercial_id": nuevo.unidad_comercial_id,
            "factor_conversion": nuevo.factor_conversion,
            "stock_minimo": nuevo.stock_minimo,
            "activo": nuevo.activo,
        }
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_producto(db: Session, producto_id: int, data: ProductoUpdate, usuario_id: int) -> Producto:
    p = obtener_producto(db, producto_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return p

    _verificar_referencias(
        db,
        cambios.get("categoria_id"),
        cambios.get("unidad_id"),
        cambios.get("unidad_comercial_id"),
    )
    if "factor_conversion" in cambios:
        _validar_factor(cambios["factor_conversion"])

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

def _stock_query():
    return """
        SELECT
            v.producto_id,
            v.codigo,
            v.nombre,
            v.unidad,
            uc.simbolo AS unidad_comercial,
            p.factor_conversion,
            v.stock_actual,
            v.stock_minimo
        FROM biofloc.vista_stock_productos v
        JOIN productos p ON p.id = v.producto_id
        JOIN unidades uc ON uc.id = p.unidad_comercial_id
        WHERE v.producto_id = :pid
    """


def obtener_stock_producto(db: Session, producto_id: int) -> StockProductoOut:
    obtener_producto(db, producto_id)  # 404 si no existe
    row = db.execute(text(_stock_query()), {"pid": producto_id}).mappings().first()
    if not row:
        return StockProductoOut(
            producto_id=producto_id,
            codigo="", nombre="", unidad="", unidad_comercial="",
            factor_conversion=Decimal("1"),
            stock_actual=Decimal("0"), stock_minimo=Decimal("0"),
        )
    return StockProductoOut(**row)


def listar_stock_productos(db: Session) -> list[StockProductoOut]:
    rows = db.execute(text("""
        SELECT
            v.producto_id,
            v.codigo,
            v.nombre,
            v.unidad,
            uc.simbolo AS unidad_comercial,
            p.factor_conversion,
            v.stock_actual,
            v.stock_minimo
        FROM biofloc.vista_stock_productos v
        JOIN productos p ON p.id = v.producto_id
        JOIN unidades uc ON uc.id = p.unidad_comercial_id
        ORDER BY v.codigo ASC
    """)).mappings().all()
    return [StockProductoOut(**r) for r in rows]
