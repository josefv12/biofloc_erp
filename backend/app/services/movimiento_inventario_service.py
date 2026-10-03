"""Servicio para movimientos históricos de inventario.

Reglas:
- Movimientos inmutables: solo listar / obtener / crear.
- Solo existen ENTRADA, SALIDA y AJUSTE.
- ENTRADA suma stock; SALIDA resta stock; AJUSTE requiere efecto_stock (+1 o -1).
- Las salidas se validan AS-OF a la fecha del movimiento.
- El costo de una salida se congela al registrarse usando el costo promedio
  ponderado del stock disponible en ese momento; no se revaloran salidas futuras.
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
from app.services.validaciones_fecha import validar_no_futuro


D2 = Decimal("0.01")


def _formato_cantidad_unidad(valor: Decimal, simbolo: str) -> str:
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    texto = texto.replace(".", ",")
    return f"{texto} {simbolo}" if simbolo else texto


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            detalle_safe[k] = float(v)
        else:
            detalle_safe[k] = v
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="movimientos_inventario",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    ))


def _validar_referencia(db: Session, referencia_tipo: str | None, referencia_id: int | None):
    if referencia_id is None or referencia_tipo is None:
        return
    if referencia_tipo == "APLICACION_BIOFLOC":
        from app.models.aplicacion_biofloc import AplicacionBiofloc
        if not db.query(AplicacionBiofloc).filter(AplicacionBiofloc.id == referencia_id).first():
            raise HTTPException(status_code=404, detail=f"Aplicación Biofloc id={referencia_id} no existe para la trazabilidad")
    elif referencia_tipo == "ALIMENTACION":
        from app.models.alimentacion import Alimentacion
        if not db.query(Alimentacion).filter(Alimentacion.id == referencia_id).first():
            raise HTTPException(status_code=404, detail=f"Alimentación id={referencia_id} no existe para la trazabilidad")


def _obtener_tipo_salida_id(db: Session) -> int:
    tipo = db.query(TipoMovimientoInventario).filter(TipoMovimientoInventario.nombre == "SALIDA").first()
    if not tipo:
        raise HTTPException(status_code=500, detail="Tipo de movimiento SALIDA no encontrado en catálogo")
    return tipo.id


def _tipo_y_efecto(tipo: TipoMovimientoInventario, efecto_stock: int | None) -> int:
    if tipo.nombre == "ENTRADA":
        if efecto_stock is not None:
            raise HTTPException(status_code=422, detail="ENTRADA no recibe efecto_stock; su efecto es +1")
        return 1
    if tipo.nombre == "SALIDA":
        if efecto_stock is not None:
            raise HTTPException(status_code=422, detail="SALIDA no recibe efecto_stock; su efecto es -1")
        return -1
    if tipo.nombre == "AJUSTE":
        if efecto_stock not in (-1, 1):
            raise HTTPException(status_code=422, detail="AJUSTE requiere efecto_stock = 1 o -1")
        return efecto_stock
    raise HTTPException(status_code=422, detail="Tipo de movimiento no permitido. Use ENTRADA, SALIDA o AJUSTE")


def _costo_promedio_stock_as_of(db: Session, producto_id: int, fecha_hora: datetime) -> Decimal:
    """Calcula el promedio ponderado del stock que existía en la fecha del evento."""
    rows = db.execute(text("""
        SELECT
            mi.cantidad,
            mi.costo_unitario,
            mi.costo_total,
            CASE
                WHEN tm.nombre = 'AJUSTE' THEN mi.efecto_stock
                ELSE tm.afecta_stock
            END AS efecto
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.tipos_movimiento_inventario tm ON tm.id = mi.tipo_movimiento_id
        WHERE mi.producto_id = :pid
          AND mi.fecha_hora <= :fecha_hora
        ORDER BY mi.fecha_hora ASC, mi.id ASC
    """), {"pid": producto_id, "fecha_hora": fecha_hora}).mappings().all()

    cantidad_stock = Decimal("0")
    valor_stock = Decimal("0")

    for row in rows:
        cantidad = Decimal(str(row["cantidad"] or 0))
        efecto = int(row["efecto"])
        costo_unitario = Decimal(str(row["costo_unitario"])) if row["costo_unitario"] is not None else None
        costo_total = Decimal(str(row["costo_total"])) if row["costo_total"] is not None else None

        if efecto == 1:
            cantidad_stock += cantidad
            if costo_total is not None:
                valor_stock += costo_total
            elif costo_unitario is not None:
                valor_stock += cantidad * costo_unitario
        else:
            if cantidad_stock <= 0:
                continue
            promedio = valor_stock / cantidad_stock
            valor_stock -= promedio * min(cantidad, cantidad_stock)
            cantidad_stock -= min(cantidad, cantidad_stock)
            if valor_stock < 0:
                valor_stock = Decimal("0")

    if cantidad_stock <= 0:
        return Decimal("0")
    return (valor_stock / cantidad_stock).quantize(D2, rounding=ROUND_HALF_UP)


def obtener_stock_producto(db: Session, producto_id: int) -> Decimal:
    row = db.execute(text("""
        SELECT COALESCE(stock_actual, 0)
        FROM biofloc.vista_stock_productos
        WHERE producto_id = :pid
    """), {"pid": producto_id}).scalar()
    return Decimal(str(row or 0))


def obtener_stock_as_of(db: Session, producto_id: int, fecha_hora: datetime) -> Decimal:
    row = db.execute(text("""
        SELECT COALESCE(SUM(
            CASE
                WHEN tm.nombre = 'AJUSTE' THEN mi.cantidad * mi.efecto_stock
                ELSE mi.cantidad * tm.afecta_stock
            END
        ), 0)
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.tipos_movimiento_inventario tm ON tm.id = mi.tipo_movimiento_id
        WHERE mi.producto_id = :pid
          AND mi.fecha_hora <= :fecha_hora
    """), {"pid": producto_id, "fecha_hora": fecha_hora}).scalar()
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
    return q.order_by(MovimientoInventario.fecha_hora.desc(), MovimientoInventario.id.desc()).all()


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

    tipo = db.query(TipoMovimientoInventario).filter(
        TipoMovimientoInventario.id == data.tipo_movimiento_id
    ).first()
    if not tipo:
        raise HTTPException(status_code=404, detail=f"Tipo movimiento id={data.tipo_movimiento_id} no existe")

    efecto = _tipo_y_efecto(tipo, data.efecto_stock)
    fecha_hora = data.fecha_hora or datetime.now(timezone.utc)
    validar_no_futuro(fecha_hora, "La fecha del movimiento de inventario")

    # Serializa las salidas/ajustes negativos para que stock y costo promedio
    # se calculen sobre el mismo estado histórico, incluso bajo concurrencia.
    if efecto == -1:
        producto = (
            db.query(Producto)
            .filter(Producto.id == data.producto_id)
            .with_for_update()
            .one()
        )

    if tipo.nombre == "AJUSTE" and not (data.observaciones and data.observaciones.strip()):
        raise HTTPException(status_code=422, detail="AJUSTE requiere una observación que explique el motivo")

    if efecto == -1:
        stock_as_of = obtener_stock_as_of(db, producto.id, fecha_hora)
        if stock_as_of < data.cantidad:
            unidad = db.query(Unidad).filter(Unidad.id == producto.unidad_id).first()
            simbolo = unidad.simbolo if unidad else ""
            raise HTTPException(
                status_code=422,
                detail=(
                    "No hay stock suficiente. Disponible: "
                    f"{_formato_cantidad_unidad(stock_as_of, simbolo)}; solicitado: "
                    f"{_formato_cantidad_unidad(Decimal(str(data.cantidad)), simbolo)}."
                ),
            )

    _validar_referencia(db, data.referencia_tipo, data.referencia_id)

    datos = data.model_dump()
    datos["fecha_hora"] = fecha_hora
    datos["registrado_por"] = usuario_id

    # Toda entrada que incremente existencias debe quedar valorada. Sin costo,
    # el promedio ponderado posterior quedaría artificialmente subvalorado.
    if efecto == 1 and data.costo_unitario is None:
        raise HTTPException(status_code=422, detail=f"{tipo.nombre} positivo requiere costo_unitario")

    # Las salidas y ajustes negativos SIEMPRE toman el costo promedio histórico
    # del stock existente en el momento del evento. No se acepta una valoración
    # manual distinta porque el costo de salida debe quedar congelado por la
    # política de promedio ponderado.
    if efecto == -1:
        costo_unitario = _costo_promedio_stock_as_of(db, producto.id, fecha_hora)
        if costo_unitario <= 0 and data.cantidad > 0:
            raise HTTPException(status_code=422, detail="No existe costo histórico disponible para valorar la salida")
        cantidad = Decimal(str(data.cantidad))
        datos["costo_unitario"] = costo_unitario
        datos["costo_total"] = (costo_unitario * cantidad).quantize(D2, rounding=ROUND_HALF_UP)

    if tipo.nombre in ("ENTRADA", "AJUSTE") and efecto == 1 and datos.get("costo_total") is None:
        datos["costo_total"] = (
            Decimal(str(data.cantidad)) * Decimal(str(data.costo_unitario))
        ).quantize(D2, rounding=ROUND_HALF_UP)

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
            "efecto_stock": nuevo.efecto_stock,
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
