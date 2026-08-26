"""
Servicio para operaciones CRUD de mediciones_biofloc.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La fecha no puede ser anterior a la fecha_siembra del lote.
- volumen_sedimentable debe ser >= 0.
- relacion_cn debe ser >= 0 (si se proporciona).
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_biofloc import MedicionBiofloc
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.medicion_biofloc import MedicionBioflocCreate
from app.services.poblacion_lote import exigir_lote_en_produccion


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_mediciones_biofloc(db: Session, lote_id: int | None = None) -> list[MedicionBiofloc]:
    q = db.query(MedicionBiofloc)
    if lote_id:
        q = q.filter(MedicionBiofloc.lote_id == lote_id)
    return q.order_by(MedicionBiofloc.fecha_hora.desc()).all()


def obtener_medicion_biofloc(db: Session, medicion_id: int) -> MedicionBiofloc:
    m = db.query(MedicionBiofloc).filter(MedicionBiofloc.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de Biofloc no encontrada")
    return m


def crear_medicion_biofloc(db: Session, data: MedicionBioflocCreate, usuario_id: int) -> MedicionBiofloc:
    # 1. Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    exigir_lote_en_produccion(db, lote)

    # 2. Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la medición de Biofloc no puede ser anterior a la siembra del lote")

    # 3. Validar volumen_sedimentable >= 0
    if data.volumen_sedimentable < 0:
        raise HTTPException(status_code=422, detail="El volumen sedimentable debe ser mayor o igual a 0")

    # 4. Validar relacion_cn >= 0 si se envía
    if data.relacion_cn is not None and data.relacion_cn < 0:
        raise HTTPException(status_code=422, detail="La relación C:N debe ser mayor o igual a 0")

    nuevo = MedicionBiofloc(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {str(e)}")

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {
            "lote_id": data.lote_id,
            "volumen_sedimentable": float(data.volumen_sedimentable),
            "relacion_cn": float(data.relacion_cn) if data.relacion_cn is not None else None
        }
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
