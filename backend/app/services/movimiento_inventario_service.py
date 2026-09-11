"""
Servicio para movimientos_inventario.
- Histórico INMUTABLE: solo listar / obtener / crear. Sin update/delete.
- Regla STOCK NEGATIVO: antes de INSERT con tipo.afecta_stock == -1,
  validar stock disponible.
- Las salidas sin costo explícito se valoran al costo promedio ponderado de las
  entradas históricas con costo hasta la fecha del movimiento. Esto permite que
  cada alimentación lleve al lote el costo del alimento realmente suministrado.
- Trazabilidad Biofloc y alimentación.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from fastapi import HTTPException

from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.tipo_movimiento_inventario import TipoMovimientoInventario
from app.models.unidad import Unidad
from app.models.auditoria import Auditoria
from app.schemas.movimiento_inventario import MovimientoInventarioCreate


def _formato_cantidad_unidad(valor: Decimal, simbolo: str) -> str:
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    texto = texto.replace(".", ",")
    if simbolo:
        return f"{texto} {simbolo}"
    return texto


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


def _validar_referencia(db: Session, referencia_tipo: str | None, referencia_id: int | None):
    if referencia_id is None or referencia_tipo is None:
        return
    if referencia_tipo == "APLICACION_BIOFLOC":
        from app.models.aplicacion_biofloc import AplicacionBiofloc
        apl = db.query(AplicacionBiofloc).filter(AplicacionBiofloc.id == referencia_id).first()
        if not apl:
            raise HTTPException(status_code=404, detail=f"Aplicación Biofloc id={referencia_id} no existe para la trazabilidad")
    elif referencia_tipo == "ALIMENTACION":
        from app.models.alimentacion import Alimentacion
        alim = db.query(Alimentacion).filter(Alimentacion.id == referencia_id).first()
        if not alim:
            raise HTTPException(status_code=404, detail=f"Alimentación id={referencia_id} no existe para la trazabilidad")


def _obtener_tipo_salida_id(db: Session) -> int:
    """Obtiene el ID del tipo de movimiento SALIDA."""
    tipo = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.nombre == "SALIDA").first()
    if not tipo:
        raise HTTPException(status_code=500, detail="Tipo de movimiento SALIDA no encontrado en catálogo")
    return tipo.id


def _costo_promedio_entrada(db: Session, producto_id: int, fecha_hora: datetime) -> Decimal:
    """Costo promedio ponderado de entradas con costo hasta el momento del consumo."""
    row = db.execute(text("""
        SELECT
            COALESCE(SUM(cantidad), 0) AS cantidad,
            COALESCE(SUM(costo_total), 0) AS costo
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.tipos_movimiento_inventario tm ON tm.id = mi.tipo_movimiento_id
        WHERE mi.producto_id = :pid
          AND tm.afecta_stock = 1
          AND mi.fecha_hora <= :fecha_hora
          AND mi.costo_unitario IS NOT NULL
          AND mi.costo_total IS NOT NULL
    """), {"pid": producto_id, "fecha_hora": fecha_hora}).mappings().one()
    cantidad = Decimal(str(row["cantidad"] or 0))
    costo = Decimal(str(row["costo"] or 0))
    if cantidad <= 0 or costo < 0:
        return Decimal("0")
    return (costo / cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def obtener_stock_producto(db: Session, producto_id: int) -> Decimal:
    """Retorna el stock actual de un producto desde la vista."""
    row = db.execute(text("""
        SELECT COALESCE(stock_actual, 0)
        FROM biofloc.vista_stock_productos
        WHERE producto_id = :pid
    """), {"pid": producto_id}).scalar()
    return Decimal(str(row or 0))


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
    producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto id={data.producto_id} no existe")
    tipo = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.id == data.tipo_movimiento_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail=f"Tipo movimiento id={data.tipo_movimiento_id} no existe")

    fecha_hora = data.fecha_hora or datetime.now(timezone.utc)

    if tipo.afecta_stock == -1:
        row = db.execute(text("""
            SELECT COALESCE(stock_actual, 0)
            FROM biofloc.vista_stock_productos
            WHERE producto_id = :pid
        """), {"pid": producto.id}).scalar()
        stock_actual = Decimal(str(row or 0))
        if (stock_actual - data.cantidad) < Decimal("0"):
            unidad = db.query(Unidad).filter(Unidad.id == producto.unidad_id).first()
            simbolo = unidad.simbolo if unidad else ""
            raise HTTPException(
                status_code=422,
                detail=(
                    "No hay stock suficiente. Disponible: "
                    f"{_formato_cantidad_unidad(stock_actual, simbolo)}; solicitado: "
                    f"{_formato_cantidad_unidad(Decimal(str(data.cantidad)), simbolo)}."
                ),
            )

    _validar_referencia(db, data.referencia_tipo, data.referencia_id)

    datos = data.model_dump()
    datos["fecha_hora"] = fecha_hora
    datos["registrado_por"] = usuario_id

    # Si una salida no trae costo, calcularlo desde las entradas históricas.
    if tipo.afecta_stock == -1 and (datos.get("costo_unitario") is None or datos.get("costo_total") is None):
        costo_unitario = _costo_promedio_entrada(db, producto.id, fecha_hora)
        cantidad = Decimal(str(data.cantidad))
        datos["costo_unitario"] = costo_unitario
        datos["costo_total"] = (costo_unitario * cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
