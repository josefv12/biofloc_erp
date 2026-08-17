"""
Servicio para movimientos_inventario.
- Histórico INMUTABLE: solo listar / obtener / crear. Sin update/delete.
- Regla STOCK NEGATIVO: antes de INSERT con tipo.afecta_stock == -1,
  consultar vista_stock_productos y si stock_actual - cantidad < 0 → HTTP 422.
- Trazabilidad Biofloc: si referencia_tipo == 'APLICACION_BIOFLOC' y referencia_id no nulo → validar existencia aplicación.
"""
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from fastapi import HTTPException

from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.tipo_movimiento_inventario import TipoMovimientoInventario
from app.models.auditoria import Auditoria
from app.schemas.movimiento_inventario import MovimientoInventarioCreate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            detalle_safe[k] = float(v)
        else:
            detalle_safe[k] = v
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="movimientos_inventario",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    )
    db.add(entrada)


def _validar_referencia_biofloc(db: Session, referencia_tipo: str | None, referencia_id: int | None):
    if referencia_tipo != "APLICACION_BIOFLOC" or referencia_id is None:
        return
    from app.models.aplicacion_biofloc import AplicacionBiofloc
    apl = db.query(AplicacionBiofloc).filter(AplicacionBiofloc.id == referencia_id).first()
    if not apl:
        raise HTTPException(status_code=404, detail=f"Aplicación Biofloc id={referencia_id} no existe para la trazabilidad")


def listar_movimientos_inventario(
    db: Session,
    producto_id: int | None = None,
    tipo_movimiento_id: int | None = None,
    referencia_tipo: str | None = None,
    referencia_id: int | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> list[MovimientoInventario]:
    q = db.query(MovimientoInventario)
    if producto_id:
        q = q.filter(MovimientoInventario.producto_id == producto_id)
    if tipo_movimiento_id:
        q = q.filter(MovimientoInventario.tipo_movimiento_id == tipo_movimiento_id)
    if referencia_tipo:
        q = q.filter(MovimientoInventario.referencia_tipo == referencia_tipo)
    if referencia_id:
        q = q.filter(MovimientoInventario.referencia_id == referencia_id)
    if fecha_desde:
        q = q.filter(MovimientoInventario.fecha_hora >= fecha_desde)
    if fecha_hasta:
        q = q.filter(MovimientoInventario.fecha_hora <= fecha_hasta)
    return q.order_by(MovimientoInventario.fecha_hora.desc()).all()


def obtener_movimiento_inventario(db: Session, movimiento_id: int) -> MovimientoInventario:
    m = db.query(MovimientoInventario).filter(MovimientoInventario.id == movimiento_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimiento de inventario no encontrado")
    return m


def crear_movimiento_inventario(
    db: Session,
    data: MovimientoInventarioCreate,
    usuario_id: int,
    flush_only: bool = False,
) -> MovimientoInventario:
    # 1. Verificar FKs obligatorias
    producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto id={data.producto_id} no existe")
    tipo = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.id == data.tipo_movimiento_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail=f"Tipo movimiento id={data.tipo_movimiento_id} no existe")

    # 2. Validar regla STOCK NEGATIVO (solo para salidas, afecta_stock == -1)
    if tipo.afecta_stock == -1:
        row = db.execute(text("""
            SELECT COALESCE(stock_actual, 0)
            FROM biofloc.vista_stock_productos
            WHERE producto_id = :pid
        """), {"pid": producto.id}).scalar()
        stock_actual = Decimal(str(row or 0))
        if (stock_actual - data.cantidad) < Decimal("0"):
            raise HTTPException(
                status_code=422,
                detail=f"Stock insuficiente: actual={stock_actual}, salida={data.cantidad}"
            )

    # 3. Trazabilidad APLICACION_BIOFLOC
    _validar_referencia_biofloc(db, data.referencia_tipo, data.referencia_id)

    # 4. Construir registro
    datos = data.model_dump()
    if datos.get("fecha_hora") is None:
        datos["fecha_hora"] = datetime.now(timezone.utc)
    datos["registrado_por"] = usuario_id

    nuevo = MovimientoInventario(**datos)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        if not flush_only:
            db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad al registrar movimiento: {str(e)}")

    _registrar_auditoria(
        db, usuario_id, "INSERT", nuevo.id,
        {
            "producto_id": nuevo.producto_id,
            "tipo_movimiento_id": nuevo.tipo_movimiento_id,
            "cantidad": nuevo.cantidad,
            "fecha_hora": nuevo.fecha_hora.isoformat() if nuevo.fecha_hora else None,
            "referencia_tipo": nuevo.referencia_tipo,
            "referencia_id": nuevo.referencia_id,
            "observaciones": nuevo.observaciones,
            "costo_unitario": nuevo.costo_unitario,
            "costo_total": nuevo.costo_total,
        }
    )

    if flush_only:
        db.refresh(nuevo)
        return nuevo

    db.commit()
    db.refresh(nuevo)
    return nuevo
