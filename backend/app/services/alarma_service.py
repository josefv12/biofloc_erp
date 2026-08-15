from decimal import Decimal
from typing import Optional, Iterable
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

from app.schemas.alarma import (
    AlarmaStockOut, CLASIF_NORMAL, CLASIF_STOCK_BAJO, CLASIF_SIN_STOCK, CLASIF_GRAVEDAD,
)

D03 = Decimal("0.001")
D0 = Decimal("0")


def clasificar_stock(stock_actual: Decimal, stock_minimo: Decimal) -> str:
    sa = Decimal(stock_actual)
    sm = Decimal(stock_minimo)
    if sa <= D0:
        return CLASIF_SIN_STOCK
    if sa <= sm:
        return CLASIF_STOCK_BAJO
    return CLASIF_NORMAL


def _q(v):
    return None if v is None else Decimal(v)


def _consulta_base(db: Session) -> str:
    return """
        SELECT v.producto_id, v.codigo, v.nombre, v.unidad,
               v.stock_actual, v.stock_minimo,
               p.activo, p.categoria_id, c.nombre AS categoria_nombre
        FROM biofloc.vista_stock_productos v
        JOIN biofloc.productos p ON p.id = v.producto_id
        LEFT JOIN biofloc.categorias_inventario c ON c.id = p.categoria_id
        WHERE 1=1
    """


def listar_alertas_stock_bajo(
    db: Session,
    *,
    clasificacion: Optional[Iterable[str]] = None,
    solo_activos: bool = True,
    categoria_id: Optional[int] = None,
    unidad: Optional[str] = None,
    producto_id: Optional[int] = None,
    incluir_normal: bool = False,
    ordenar_por_gravedad: bool = True,
) -> list[AlarmaStockOut]:
    sql = _consulta_base(db)
    params: dict = {}
    if solo_activos:
        sql += "\n AND p.activo = TRUE"
    if categoria_id is not None:
        sql += "\n AND p.categoria_id = :categoria_id"
        params["categoria_id"] = categoria_id
    if unidad:
        sql += "\n AND v.unidad = :unidad"
        params["unidad"] = unidad
    if producto_id is not None:
        sql += "\n AND v.producto_id = :producto_id"
        params["producto_id"] = producto_id

    rows = db.execute(text(sql), params).mappings().all()
    out: list[AlarmaStockOut] = []
    filtro_clasif = set(clasificacion) if clasificacion else None
    for r in rows:
        sa = _q(r["stock_actual"]) or D0
        sm = _q(r["stock_minimo"]) or D0
        c = clasificar_stock(sa, sm)
        if not incluir_normal and c == CLASIF_NORMAL:
            continue
        if filtro_clasif and c not in filtro_clasif:
            continue
        out.append(
            AlarmaStockOut(
                producto_id=int(r["producto_id"]),
                codigo=str(r["codigo"]),
                nombre=str(r["nombre"]),
                unidad=str(r["unidad"]),
                stock_actual=sa.quantize(D03),
                stock_minimo=sm.quantize(D03),
                diferencia=(sa - sm).quantize(D03),
                clasificacion=c,
                activo=bool(r["activo"]),
                categoria_id=int(r["categoria_id"]),
                categoria_nombre=r["categoria_nombre"],
            )
        )
    if ordenar_por_gravedad:
        out.sort(key=lambda a: (CLASIF_GRAVEDAD[a.clasificacion], a.diferencia, a.codigo))
    return out


def obtener_alerta_producto(db: Session, producto_id: int) -> AlarmaStockOut:
    sql = _consulta_base(db) + "\n AND v.producto_id = :producto_id"
    row = db.execute(text(sql), {"producto_id": producto_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
    sa = _q(row["stock_actual"]) or D0
    sm = _q(row["stock_minimo"]) or D0
    c = clasificar_stock(sa, sm)
    return AlarmaStockOut(
        producto_id=int(row["producto_id"]),
        codigo=str(row["codigo"]),
        nombre=str(row["nombre"]),
        unidad=str(row["unidad"]),
        stock_actual=sa.quantize(D03),
        stock_minimo=sm.quantize(D03),
        diferencia=(sa - sm).quantize(D03),
        clasificacion=c,
        activo=bool(row["activo"]),
        categoria_id=int(row["categoria_id"]),
        categoria_nombre=row["categoria_nombre"],
    )
