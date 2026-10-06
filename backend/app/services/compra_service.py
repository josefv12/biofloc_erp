from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.compra import Compra
from app.models.detalle_compra import DetalleCompra
from app.models.producto import Producto
from app.models.tipo_movimiento_inventario import TipoMovimientoInventario
from app.models.auditoria import Auditoria
from app.schemas.compra import CompraCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.movimiento_inventario_service import crear_movimiento_inventario


NOMBRE_TIPO_ENTRADA = "ENTRADA"
REFERENCIA_TIPO_DETALLE_COMPRA = "DETALLE_COMPRA"


def _tipo_movimiento_entrada(db: Session) -> TipoMovimientoInventario:
    tipo = (
        db.query(TipoMovimientoInventario)
        .filter(TipoMovimientoInventario.nombre == NOMBRE_TIPO_ENTRADA)
        .first()
    )
    if not tipo:
        raise HTTPException(status_code=500, detail="Catálogo interno incompleto: falta el movimiento ENTRADA.")
    if int(tipo.afecta_stock) != 1:
        raise HTTPException(status_code=500, detail="Configuración interna inválida para el movimiento ENTRADA.")
    return tipo


def _registrar_auditoria(db: Session, usuario_id: int, tabla: str, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            detalle_safe[k] = float(v)
        elif isinstance(v, (datetime, date)):
            detalle_safe[k] = v.isoformat()
        else:
            detalle_safe[k] = v
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla=tabla,
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    )
    db.add(entrada)


def _quant2(d: Decimal) -> Decimal:
    return Decimal(d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quant3(d: Decimal) -> Decimal:
    return Decimal(d).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def crear_compra(db: Session, payload: CompraCreate, usuario_id: int) -> Compra:
    if not payload.detalles or len(payload.detalles) == 0:
        raise HTTPException(status_code=422, detail="La compra requiere al menos 1 detalle")

    detalles_procesados = []
    total_calculado = Decimal("0")

    for idx, din in enumerate(payload.detalles, start=1):
        prod = db.query(Producto).filter(Producto.id == din.producto_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"El producto no existe (detalle #{idx})")
        if not prod.activo:
            raise HTTPException(status_code=422, detail=f"El producto está inactivo (detalle #{idx})")

        cantidad = _quant3(din.cantidad)
        pu = _quant2(din.precio_unitario)
        if cantidad <= Decimal("0"):
            raise HTTPException(status_code=422, detail=f"La cantidad debe ser > 0 (detalle #{idx})")
        if pu < Decimal("0"):
            raise HTTPException(status_code=422, detail=f"El precio unitario debe ser >= 0 (detalle #{idx})")
        subtotal = _quant2(cantidad * pu)
        total_calculado += subtotal
        detalles_procesados.append({
            "producto_id": prod.id,
            "cantidad": cantidad,
            "precio_unitario": pu,
            "subtotal": subtotal,
        })

    tipo_entrada = _tipo_movimiento_entrada(db)
    try:
        compra = Compra(
            fecha=payload.fecha,
            proveedor=(payload.proveedor or None),
            total=Decimal("0"),
            observaciones=(payload.observaciones or None),
            registrado_por=usuario_id,
        )
        db.add(compra)
        db.flush()

        detalle_objetos: list[tuple[DetalleCompra, int]] = []

        for dp in detalles_procesados:
            detalle = DetalleCompra(
                compra_id=compra.id,
                producto_id=dp["producto_id"],
                cantidad=dp["cantidad"],
                precio_unitario=dp["precio_unitario"],
                subtotal=dp["subtotal"],
            )
            db.add(detalle)
            db.flush()

            mov_create = MovimientoInventarioCreate(
                producto_id=dp["producto_id"],
                tipo_movimiento_id=tipo_entrada.id,
                cantidad=dp["cantidad"],
                fecha_hora=datetime.combine(payload.fecha, datetime.max.time(), tzinfo=timezone.utc),
                referencia_tipo=REFERENCIA_TIPO_DETALLE_COMPRA,
                referencia_id=detalle.id,
                observaciones=f"Compra #{compra.id} generada",
                costo_unitario=dp["precio_unitario"],
                costo_total=dp["subtotal"],
            )
            mov = crear_movimiento_inventario(db, mov_create, usuario_id=usuario_id, flush_only=True)
            detalle_objetos.append((detalle, mov.id))

        compra.total = _quant2(total_calculado)
        db.flush()

        _registrar_auditoria(
            db, usuario_id, tabla="compras", accion="INSERT", registro_id=compra.id,
            detalle={
                "fecha": compra.fecha,
                "proveedor": compra.proveedor,
                "total": compra.total,
                "observaciones": compra.observaciones,
                "registrado_por": compra.registrado_por,
                "cantidad_detalles": len(detalle_objetos),
            },
        )
        for detalle, mov_id in detalle_objetos:
            _registrar_auditoria(
                db, usuario_id, tabla="detalles_compra", accion="INSERT", registro_id=detalle.id,
                detalle={
                    "compra_id": detalle.compra_id,
                    "producto_id": detalle.producto_id,
                    "cantidad": detalle.cantidad,
                    "precio_unitario": detalle.precio_unitario,
                    "subtotal": detalle.subtotal,
                    "movimiento_inventario_id": mov_id,
                },
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No fue posible registrar la compra por una regla de integridad.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible registrar la compra por un error interno.")

    db.refresh(compra)
    _ = compra.detalles
    return compra


def listar_compras(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    proveedor: str | None = None,
    producto_id: int | None = None,
    registrado_por: int | None = None,
) -> list[Compra]:
    q = db.query(Compra).options(joinedload(Compra.detalles))

    if producto_id is not None:
        q = q.filter(
            Compra.id.in_(
                db.query(DetalleCompra.compra_id).filter(DetalleCompra.producto_id == producto_id)
            )
        )
    if fecha_desde:
        q = q.filter(Compra.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Compra.fecha <= fecha_hasta)
    if proveedor:
        q = q.filter(Compra.proveedor.ilike(f"%{proveedor}%"))
    if registrado_por:
        q = q.filter(Compra.registrado_por == registrado_por)

    return q.order_by(Compra.fecha.desc(), Compra.id.desc()).all()


def obtener_compra(db: Session, compra_id: int) -> Compra:
    c = (
        db.query(Compra)
        .options(joinedload(Compra.detalles))
        .filter(Compra.id == compra_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return c


def obtener_movimientos_asociados(db: Session, compra_id: int) -> list[dict]:
    from app.models.movimiento_inventario import MovimientoInventario
    detalle_ids = [d.id for d in db.query(DetalleCompra).filter(DetalleCompra.compra_id == compra_id).all()]
    if not detalle_ids:
        return []
    movs = (
        db.query(MovimientoInventario)
        .filter(
            MovimientoInventario.referencia_tipo == REFERENCIA_TIPO_DETALLE_COMPRA,
            MovimientoInventario.referencia_id.in_(detalle_ids),
        )
        .order_by(MovimientoInventario.id.asc())
        .all()
    )
    out = []
    for m in movs:
        out.append({
            "id": m.id,
            "producto_id": m.producto_id,
            "tipo_movimiento_id": m.tipo_movimiento_id,
            "cantidad": float(m.cantidad) if m.cantidad is not None else None,
            "fecha_hora": m.fecha_hora.isoformat() if m.fecha_hora else None,
            "referencia_tipo": m.referencia_tipo,
            "referencia_id": m.referencia_id,
            "observaciones": m.observaciones,
            "registrado_por": m.registrado_por,
            "costo_unitario": float(m.costo_unitario) if m.costo_unitario is not None else None,
            "costo_total": float(m.costo_total) if m.costo_total is not None else None,
        })
    return out


def editar_compra(db: Session, compra_id: int, payload: CompraCreate, usuario_id: int) -> Compra:
    """Edita una compra y sincroniza sus movimientos de entrada.

    Se permite modificar fecha, proveedor, observaciones, cantidades y precios.
    Para preservar la trazabilidad histórica, la cantidad de líneas y los
    productos de cada línea deben mantenerse. Los movimientos posteriores de
    esos productos se revaloran con promedio ponderado móvil.
    """
    compra = (
        db.query(Compra)
        .options(joinedload(Compra.detalles))
        .filter(Compra.id == compra_id)
        .with_for_update()
        .first()
    )
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if not payload.detalles:
        raise HTTPException(status_code=422, detail="La compra requiere al menos 1 detalle")

    actuales = sorted(compra.detalles, key=lambda d: d.id)
    nuevos = list(payload.detalles)
    if len(actuales) != len(nuevos):
        raise HTTPException(
            status_code=422,
            detail="Para editar una compra existente debes conservar el mismo número de líneas. "
                   "Si necesitas agregar o quitar productos, registra una nueva compra y corrige la anterior."
        )

    # Mantener los productos de cada línea evita romper referencias históricas.
    for idx, (detalle, din) in enumerate(zip(actuales, nuevos), start=1):
        if int(detalle.producto_id) != int(din.producto_id):
            raise HTTPException(
                status_code=422,
                detail=f"No se puede cambiar el producto de la línea #{idx} de una compra ya registrada. "
                       "Puedes modificar cantidad y precio."
            )

    detalles_procesados = []
    total_calculado = Decimal("0")
    for idx, (detalle, din) in enumerate(zip(actuales, nuevos), start=1):
        prod = db.query(Producto).filter(Producto.id == din.producto_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"El producto no existe (detalle #{idx})")
        cantidad = _quant3(din.cantidad)
        pu = _quant2(din.precio_unitario)
        if cantidad <= 0:
            raise HTTPException(status_code=422, detail=f"La cantidad debe ser > 0 (detalle #{idx})")
        if pu < 0:
            raise HTTPException(status_code=422, detail=f"El precio unitario debe ser >= 0 (detalle #{idx})")
        subtotal = _quant2(cantidad * pu)
        total_calculado += subtotal
        detalles_procesados.append((detalle, cantidad, pu, subtotal))

    from app.models.movimiento_inventario import MovimientoInventario

    tipo_entrada = _tipo_movimiento_entrada(db)
    cambios_productos = set()
    try:
        # Actualizar compra y detalles primero.
        compra.fecha = payload.fecha
        compra.proveedor = payload.proveedor or None
        compra.observaciones = payload.observaciones or None
        compra.total = _quant2(total_calculado)

        for detalle, cantidad, pu, subtotal in detalles_procesados:
            mov = (
                db.query(MovimientoInventario)
                .filter(
                    MovimientoInventario.referencia_tipo == REFERENCIA_TIPO_DETALLE_COMPRA,
                    MovimientoInventario.referencia_id == detalle.id,
                )
                .with_for_update()
                .first()
            )
            if not mov:
                raise HTTPException(
                    status_code=409,
                    detail=f"La línea #{detalle.id} no tiene movimiento de inventario asociado; no se puede editar con seguridad."
                )
            if int(mov.tipo_movimiento_id) != int(tipo_entrada.id):
                raise HTTPException(
                    status_code=409,
                    detail=f"El movimiento asociado a la línea #{detalle.id} no es una entrada de inventario."
                )

            detalle.cantidad = cantidad
            detalle.precio_unitario = pu
            detalle.subtotal = subtotal

            mov.cantidad = cantidad
            mov.fecha_hora = datetime.combine(payload.fecha, datetime.max.time(), tzinfo=timezone.utc)
            mov.costo_unitario = pu
            mov.costo_total = subtotal
            mov.observaciones = f"Compra #{compra.id} editada"
            cambios_productos.add(int(detalle.producto_id))

        db.flush()

        # Revalorar todas las salidas posteriores de los productos afectados.
        # Esto es necesario porque el promedio ponderado puede cambiar al editar
        # una compra histórica.
        for producto_id in sorted(cambios_productos):
            rows = (
                db.query(MovimientoInventario)
                .join(TipoMovimientoInventario, TipoMovimientoInventario.id == MovimientoInventario.tipo_movimiento_id)
                .filter(MovimientoInventario.producto_id == producto_id)
                .order_by(MovimientoInventario.fecha_hora.asc(), MovimientoInventario.id.asc())
                .with_for_update()
                .all()
            )
            stock = Decimal("0")
            valor = Decimal("0")
            for mov in rows:
                afecta = int(mov.tipo_movimiento.afecta_stock)
                cantidad = Decimal(str(mov.cantidad))
                if afecta == 1:
                    if mov.costo_unitario is None:
                        raise HTTPException(
                            status_code=422,
                            detail=f"El producto #{producto_id} tiene una entrada sin costo y no puede revalorarse."
                        )
                    stock += cantidad
                    valor += cantidad * Decimal(str(mov.costo_unitario))
                elif afecta == -1:
                    if cantidad > stock:
                        raise HTTPException(
                            status_code=422,
                            detail=f"La edición de la compra dejaría stock negativo para el producto #{producto_id}. "
                                   "Corrige la fecha o cantidad de la compra."
                        )
                    if stock <= 0:
                        raise HTTPException(
                            status_code=422,
                            detail=f"No se puede revalorar el producto #{producto_id}: stock inválido antes de una salida."
                        )
                    promedio = (valor / stock).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    mov.costo_unitario = promedio
                    mov.costo_total = _quant2(promedio * cantidad)
                    valor -= cantidad * promedio
                    stock -= cantidad

        _registrar_auditoria(
            db, usuario_id, tabla="compras", accion="UPDATE", registro_id=compra.id,
            detalle={
                "fecha": compra.fecha,
                "proveedor": compra.proveedor,
                "total": compra.total,
                "observaciones": compra.observaciones,
                "cantidad_detalles": len(actuales),
                "productos_revalorados": sorted(cambios_productos),
            },
        )
        for detalle, cantidad, pu, subtotal in detalles_procesados:
            _registrar_auditoria(
                db, usuario_id, tabla="detalles_compra", accion="UPDATE", registro_id=detalle.id,
                detalle={
                    "compra_id": detalle.compra_id,
                    "producto_id": detalle.producto_id,
                    "cantidad": cantidad,
                    "precio_unitario": pu,
                    "subtotal": subtotal,
                },
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No fue posible editar la compra por una regla de integridad.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible editar la compra por un error interno.")

    db.refresh(compra)
    _ = compra.detalles
    return compra
