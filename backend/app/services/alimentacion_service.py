"""
Servicio para operaciones CRUD de alimentaciones.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La fecha no puede ser anterior a la fecha_siembra del lote.
- producto_id debe ser válido (se atrapa el error de Integridad de la BD).
- La auditoría registra INSERT en creación.
- Al crear alimentación se genera automáticamente un movimiento de SALIDA de inventario.
- La operación es atómica: si el movimiento falla, no se crea la alimentación.
- No se expone UPDATE ni DELETE.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.alimentacion import Alimentacion
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.alimentacion import AlimentacionCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.movimiento_inventario_service import crear_movimiento_inventario, _obtener_tipo_salida_id
from app.services.poblacion_lote import exigir_lote_en_produccion


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="alimentaciones",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_alimentaciones(db: Session, lote_id: int | None = None) -> list[Alimentacion]:
    q = db.query(Alimentacion)
    if lote_id:
        q = q.filter(Alimentacion.lote_id == lote_id)
    return q.order_by(Alimentacion.fecha_hora.desc()).all()


def obtener_alimentacion(db: Session, alimentacion_id: int) -> Alimentacion:
    a = db.query(Alimentacion).filter(Alimentacion.id == alimentacion_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alimentacion no encontrada")
    return a


def crear_alimentacion(db: Session, data: AlimentacionCreate, usuario_id: int) -> Alimentacion:
    # Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    exigir_lote_en_produccion(db, lote)

    # Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la alimentación no puede ser anterior a la siembra del lote")

    # Obtener tipo SALIDA antes de empezar la transacción
    tipo_salida_id = _obtener_tipo_salida_id(db)

    # Crear registro de alimentación (flush, no commit)
    nuevo = Alimentacion(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e)
        if "productos" in error_msg or "producto_id" in error_msg:
            raise HTTPException(status_code=404, detail=f"Producto id={data.producto_id} no existe")
        raise HTTPException(status_code=400, detail="Error de integridad en base de datos")

    # Crear movimiento de SALIDA de inventario (transaccional, flush_only=True)
    # La validación de stock ocurre dentro de crear_movimiento_inventario
    mov_data = MovimientoInventarioCreate(
        producto_id=data.producto_id,
        tipo_movimiento_id=tipo_salida_id,
        cantidad=Decimal(str(data.cantidad)),
        fecha_hora=data.fecha_hora,
        referencia_tipo="ALIMENTACION",
        referencia_id=nuevo.id,
        observaciones=f"Consumo automático - Lote {lote.codigo}",
    )
    try:
        crear_movimiento_inventario(db, mov_data, usuario_id, flush_only=True)
    except HTTPException:
        db.rollback()
        raise

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {"lote_id": data.lote_id, "producto_id": data.producto_id, "cantidad": float(data.cantidad), "inventario": True}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
