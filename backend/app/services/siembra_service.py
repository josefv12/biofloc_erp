from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.lote import Lote, EstadoLote
from app.models.producto import Producto
from app.models.categoria_inventario import CategoriaInventario
from app.models.auditoria import Auditoria
from app.schemas.siembra import SiembraLoteCreate, SiembraLoteOut
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.movimiento_inventario_service import crear_movimiento_inventario, _obtener_tipo_salida_id


def sembrar_lote(db: Session, lote_id: int, data: SiembraLoteCreate, usuario_id: int) -> SiembraLoteOut:
    lote = (
        db.query(Lote)
        .join(Lote.estado)
        .filter(Lote.id == lote_id)
        .with_for_update()
        .first()
    )
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    if lote.estado.nombre != "PLANIFICADO":
        raise HTTPException(status_code=422, detail="Solo un lote PLANIFICADO puede ser sembrado. La siembra no puede registrarse dos veces.")
    if data.fecha_hora.date() != lote.fecha_siembra:
        raise HTTPException(status_code=422, detail=f"La fecha de siembra debe coincidir con la fecha prevista del lote: {lote.fecha_siembra.isoformat()}.")

    producto = db.query(Producto).filter(Producto.id == data.producto_id, Producto.activo == True).first()
    if not producto:
        raise HTTPException(status_code=404, detail="El producto de alevinos no existe o está inactivo")
    categoria = db.query(CategoriaInventario).filter(CategoriaInventario.id == producto.categoria_id).first()
    if not categoria or categoria.nombre != "ALEVINOS":
        raise HTTPException(status_code=422, detail="El producto seleccionado debe pertenecer a la categoría ALEVINOS")

    tipo_salida_id = _obtener_tipo_salida_id(db)
    mov_data = MovimientoInventarioCreate(
        producto_id=data.producto_id,
        tipo_movimiento_id=tipo_salida_id,
        cantidad=Decimal(data.cantidad),
        fecha_hora=data.fecha_hora,
        referencia_tipo="SIEMBRA",
        referencia_id=lote.id,
        observaciones=f"Siembra - Lote {lote.codigo}",
    )

    try:
        mov = crear_movimiento_inventario(db, mov_data, usuario_id, flush_only=True)
        lote.cantidad_sembrada = data.cantidad
        if data.peso_inicial_promedio_g is not None:
            lote.peso_inicial_promedio_g = data.peso_inicial_promedio_g
        estado_activo = db.query(EstadoLote).filter(EstadoLote.nombre == "ACTIVO").first()
        if not estado_activo:
            raise HTTPException(status_code=500, detail="No existe el estado ACTIVO en el catálogo de lotes")
        lote.estado_id = estado_activo.id
        db.add(Auditoria(
            usuario_id=usuario_id,
            tabla="lotes",
            registro_id=lote.id,
            accion="SIEMBRA",
            detalle={
                "producto_id": data.producto_id,
                "cantidad_sembrada": data.cantidad,
                "movimiento_inventario_id": mov.id,
                "costo_unitario": float(mov.costo_unitario or 0),
                "costo_total": float(mov.costo_total or 0),
            },
        ))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"No fue posible registrar la siembra: {exc.orig}")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible registrar la siembra por un error interno")

    db.refresh(lote)
    db.refresh(mov)
    return SiembraLoteOut(
        lote_id=lote.id,
        codigo=lote.codigo,
        producto_id=data.producto_id,
        cantidad_sembrada=lote.cantidad_sembrada,
        costo_unitario=float(mov.costo_unitario or 0),
        costo_total=float(mov.costo_total or 0),
        fecha_hora=mov.fecha_hora,
        movimiento_inventario_id=mov.id,
    )
