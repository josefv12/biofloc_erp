"""
Servicio para operaciones CRUD de aplicaciones_biofloc.

Reglas aplicadas:
- lote_id debe existir.
- tipo_aplicacion_id debe existir.
- fecha_hora no puede ser anterior a fecha_siembra del lote.
- cantidad: NULL permitido; si se envía debe ser >= 0.
- producto_id: columna libre (BIGINT NULL, sin FK en DDL). Si se envía
  y no existe en la tabla productos se captura el IntegrityError.
  Nota: Inventario no implementado aún.
- No se expone UPDATE ni DELETE (registros históricos).
- Auditoría INSERT por cada creación exitosa.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.aplicacion_biofloc import AplicacionBiofloc
from app.models.lote import Lote
from app.models.tipo_aplicacion_biofloc import TipoAplicacionBiofloc
from app.models.auditoria import Auditoria
from app.schemas.aplicacion_biofloc import AplicacionBioflocCreate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="aplicaciones_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_aplicaciones_biofloc(
    db: Session,
    lote_id: int | None = None
) -> list[AplicacionBiofloc]:
    q = db.query(AplicacionBiofloc)
    if lote_id:
        q = q.filter(AplicacionBiofloc.lote_id == lote_id)
    return q.order_by(AplicacionBiofloc.fecha_hora.desc()).all()


def obtener_aplicacion_biofloc(db: Session, aplicacion_id: int) -> AplicacionBiofloc:
    a = db.query(AplicacionBiofloc).filter(AplicacionBiofloc.id == aplicacion_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Aplicación Biofloc no encontrada")
    return a


def crear_aplicacion_biofloc(db: Session, data: AplicacionBioflocCreate, usuario_id: int) -> AplicacionBiofloc:
    # 1. Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")

    # 2. Validar tipo_aplicacion_id
    tipo = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.id == data.tipo_aplicacion_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail=f"Tipo de aplicación Biofloc id={data.tipo_aplicacion_id} no existe")

    # 3. Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la aplicación no puede ser anterior a la siembra del lote")

    # 4. Validar cantidad >= 0 si se proporciona
    if data.cantidad is not None and data.cantidad < 0:
        raise HTTPException(status_code=422, detail="La cantidad debe ser mayor o igual a 0")

    nuevo = AplicacionBiofloc(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {str(e)}")

    # Serializar Decimal para JSONB
    detalle = {
        "lote_id": data.lote_id,
        "tipo_aplicacion_id": data.tipo_aplicacion_id,
        "producto_id": data.producto_id,
        "cantidad": float(data.cantidad) if isinstance(data.cantidad, Decimal) else data.cantidad,
    }

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, detalle)
    db.commit()
    db.refresh(nuevo)
    return nuevo
