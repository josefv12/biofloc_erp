"""Ventas FINANZAS COMERCIALES (sin movimientos_inventario).

- Venta INMUTABLE: POST + GET list + GET detalle.
- Atómica: 1 transacción (venta + detalles + auditoría INSERT) con rollback 0 huellas.
- Subtotal / total siempre server-side.
- La cantidad vendida se expresa en kg de biomasa cosechada.
- Una venta nunca puede superar la biomasa cosechada y aún disponible del lote.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from fastapi import HTTPException

from app.models.venta import Venta, DetalleVenta
from app.services.validaciones_fecha import validar_fecha_no_futura
from app.models.auditoria import Auditoria
from app.models.lote import Lote
from app.models.cosecha import Cosecha
from app.schemas.venta import VentaCreate


def _norm(v, prec=2):
    return Decimal(v).quantize(Decimal(f"0.{'0'*prec}"), rounding=ROUND_HALF_UP)


def _audit(db: Session, usuario_id: int, accion: str, tabla: str, registro_id: int, detalle: dict):
    safe = {}
    for k, v in detalle.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v
    db.add(Auditoria(usuario_id=usuario_id, tabla=tabla,
                     registro_id=registro_id, accion=accion, detalle=safe))


def listar_ventas(db: Session,
                  fecha_desde: Optional[date] = None,
                  fecha_hasta: Optional[date] = None,
                  cliente: Optional[str] = None,
                  lote_id: Optional[int] = None,
                  registrado_por: Optional[int] = None):
    q = db.query(Venta).options(joinedload(Venta.detalles).joinedload(DetalleVenta.lote))
    if fecha_desde:
        q = q.filter(Venta.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Venta.fecha <= fecha_hasta)
    if cliente:
        q = q.filter(Venta.cliente.ilike(f"%{cliente}%"))
    if registrado_por is not None:
        q = q.filter(Venta.registrado_por == registrado_por)
    if lote_id is not None:
        q = q.filter(
            Venta.id.in_(
                db.query(DetalleVenta.venta_id).filter(DetalleVenta.lote_id == lote_id)
            )
        )
    return q.order_by(Venta.fecha.desc(), Venta.id.desc()).all()


def obtener_venta(db: Session, venta_id: int) -> Venta:
    v = db.query(Venta).options(joinedload(Venta.detalles).joinedload(DetalleVenta.lote)) \
        .filter(Venta.id == venta_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return v


def _fin_dia_colombia_utc(fecha: date) -> datetime:
    """Límite superior exclusivo para una fecha comercial en America/Bogota."""
    siguiente = fecha + timedelta(days=1)
    return datetime.combine(
        siguiente,
        time.min,
        tzinfo=ZoneInfo("America/Bogota"),
    ).astimezone(timezone.utc)


def _validar_disponibilidad_lotes(db: Session, detalles: list, fecha_venta: date) -> None:
    """Bloquea cada lote y valida la biomasa disponible para venta.

    La cantidad comercial de ventas es kg de biomasa cosechada. El bloqueo de la
    fila del lote hace que dos ventas concurrentes no puedan consumir la misma
    disponibilidad. El trigger 004 replica esta regla en PostgreSQL para
    operaciones que no pasen por este servicio.
    """
    solicitada_por_lote: dict[int, Decimal] = {}
    for d in detalles:
        solicitada_por_lote[d.lote_id] = solicitada_por_lote.get(d.lote_id, Decimal("0")) + Decimal(d.cantidad)

    # Orden determinista de bloqueo: evita deadlocks entre ventas concurrentes
    # que involucren los mismos lotes en distinto orden.
    for lote_id in sorted(solicitada_por_lote):
        solicitada = solicitada_por_lote[lote_id]
        lote = (
            db.query(Lote)
            .filter(Lote.id == lote_id)
            .with_for_update()
            .first()
        )
        if not lote:
            raise HTTPException(status_code=404, detail=f"Lote {lote_id} no existe")
        if fecha_venta < lote.fecha_siembra:
            raise HTTPException(
                status_code=422,
                detail=f"La fecha de la venta no puede ser anterior a la siembra del lote {lote.codigo}",
            )
        if lote.fecha_cierre is not None and fecha_venta > lote.fecha_cierre:
            raise HTTPException(
                status_code=422,
                detail=f"La fecha de la venta no puede ser posterior al cierre del lote {lote.codigo}",
            )

        limite_cosecha = _fin_dia_colombia_utc(fecha_venta)
        cosechado = db.query(func.coalesce(func.sum(Cosecha.peso_total_kg), 0)).filter(
            Cosecha.lote_id == lote_id,
            Cosecha.fecha_hora < limite_cosecha,
        ).scalar()
        vendido = db.query(func.coalesce(func.sum(DetalleVenta.cantidad), 0)).join(
            Venta, Venta.id == DetalleVenta.venta_id
        ).filter(
            DetalleVenta.lote_id == lote_id,
            Venta.fecha <= fecha_venta,
        ).scalar()
        disponible = max(Decimal(str(cosechado or 0)) - Decimal(str(vendido or 0)), Decimal("0"))

        if solicitada > disponible:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Biomasa insuficiente para vender del lote {lote.codigo}. "
                    f"Disponible: {_norm(disponible, 3)} kg; solicitado: {_norm(solicitada, 3)} kg."
                ),
            )


def _validar_ventas_historicas_no_superan_cosechas(db: Session, lote_ids: list[int]) -> None:
    """Reconstruye la disponibilidad comercial por fecha para detectar ventas retroactivas."""
    from sqlalchemy import text

    for lote_id in sorted(set(lote_ids)):
        filas = db.execute(text("""
            WITH cosechas AS (
                SELECT
                    (c.fecha_hora AT TIME ZONE 'America/Bogota')::date AS fecha,
                    SUM(c.peso_total_kg) AS kg
                FROM biofloc.cosechas c
                WHERE c.lote_id = :lote_id
                GROUP BY 1
            ),
            ventas AS (
                SELECT
                    v.fecha,
                    SUM(d.cantidad) AS kg
                FROM biofloc.ventas v
                JOIN biofloc.detalles_venta d ON d.venta_id = v.id
                WHERE d.lote_id = :lote_id
                GROUP BY v.fecha
            ),
            fechas AS (
                SELECT fecha FROM cosechas
                UNION
                SELECT fecha FROM ventas
            )
            SELECT
                f.fecha,
                COALESCE((SELECT SUM(c.kg) FROM cosechas c WHERE c.fecha <= f.fecha), 0) AS cosechado,
                COALESCE((SELECT SUM(v.kg) FROM ventas v WHERE v.fecha <= f.fecha), 0) AS vendido
            FROM fechas f
            ORDER BY f.fecha
        """), {"lote_id": lote_id}).mappings().all()

        for fila in filas:
            if Decimal(str(fila["vendido"])) > Decimal(str(fila["cosechado"])):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"La secuencia histórica de ventas del lote {lote_id} "
                        f"supera la biomasa cosechada al {fila['fecha']}"
                    ),
                )


def crear_venta(db: Session, data: VentaCreate, usuario_id: int) -> Venta:
    validar_fecha_no_futura(data.fecha, "La fecha de la venta")
    if not data.detalles:
        raise HTTPException(status_code=422, detail="La venta debe tener al menos 1 detalle")

    # Validaciones sin escrituras. La disponibilidad se valida dentro de la
    # transacción y con bloqueo de los lotes para proteger concurrencia.
    for idx, d in enumerate(data.detalles, start=1):
        if Decimal(d.cantidad) <= 0:
            raise HTTPException(status_code=422, detail=f"La cantidad debe ser mayor que 0 (detalle #{idx})")
        if Decimal(d.precio_unitario) < 0:
            raise HTTPException(status_code=422, detail=f"El precio unitario debe ser >= 0 (detalle #{idx})")

    try:
        _validar_disponibilidad_lotes(db, data.detalles, data.fecha)

        total = Decimal(0)
        detalles_obj = []
        for d in data.detalles:
            cant = _norm(d.cantidad, 3)
            pu = _norm(d.precio_unitario, 2)
            subtotal = _norm(cant * pu, 2)
            total += subtotal
            detalles_obj.append(DetalleVenta(
                lote_id=d.lote_id,
                cantidad=cant,
                precio_unitario=pu,
                subtotal=subtotal,
            ))
        total = _norm(total, 2)

        venta = Venta(
            fecha=data.fecha,
            cliente=(data.cliente.strip() if data.cliente else None),
            total=total,
            observaciones=(data.observaciones.strip() if data.observaciones else None),
            registrado_por=usuario_id,
            detalles=detalles_obj,
        )
        db.add(venta)
        db.flush()

        _validar_ventas_historicas_no_superan_cosechas(
            db, [d.lote_id for d in data.detalles]
        )

        _audit(db, usuario_id, "INSERT", "ventas", venta.id, {
            "fecha": venta.fecha,
            "cliente": venta.cliente,
            "total": Decimal(venta.total),
            "observaciones": venta.observaciones,
            "detalles_count": len(venta.detalles),
        })
        for dv in venta.detalles:
            _audit(db, usuario_id, "INSERT", "detalles_venta", dv.id, {
                "venta_id": venta.id,
                "venta_cliente": venta.cliente,
                "venta_obs": venta.observaciones,
                "lote_id": dv.lote_id,
                "cantidad": Decimal(dv.cantidad),
                "precio_unitario": Decimal(dv.precio_unitario),
                "subtotal": Decimal(dv.subtotal),
            })

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No fue posible registrar la venta por una regla de integridad.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible registrar la venta por un error interno.")

    return obtener_venta(db, venta.id)
