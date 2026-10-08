"""
Servicio para mediciones de Biofloc asociadas al ciclo productivo (lote).
El lote puede estar PLANIFICADO (pre-siembra) o ACTIVO (producción).
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_biofloc import MedicionBiofloc
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.medicion_biofloc import MedicionBioflocCreate
from app.services.validaciones_temporales import validar_evento_lote, validar_evento_no_futuro

ESTADOS_MEDICION_PERMITIDOS = {"PLANIFICADO", "ACTIVO"}

def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    ))

def listar_mediciones_biofloc(db: Session, lote_id: int | None = None) -> list[MedicionBiofloc]:
    q = db.query(MedicionBiofloc)
    if lote_id is not None:
        q = q.filter(MedicionBiofloc.lote_id == lote_id)
    return q.order_by(MedicionBiofloc.fecha_hora.desc()).all()

def obtener_medicion_biofloc(db: Session, medicion_id: int) -> MedicionBiofloc:
    m = db.query(MedicionBiofloc).filter(MedicionBiofloc.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de Biofloc no encontrada")
    return m

def crear_medicion_biofloc(db: Session, data: MedicionBioflocCreate, usuario_id: int) -> MedicionBiofloc:
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")

    if lote.estado.nombre not in ESTADOS_MEDICION_PERMITIDOS:
        raise HTTPException(status_code=422, detail="Solo se pueden registrar mediciones para lotes PLANIFICADOS o ACTIVOS.")

    validar_evento_no_futuro(data.fecha_hora, "la medición de Biofloc")
    if lote.estado.nombre == "ACTIVO":
        validar_evento_lote(data.fecha_hora, lote.fecha_siembra, "la medición de Biofloc")
    else:
        if data.fecha_hora.date() > lote.fecha_siembra:
            raise HTTPException(status_code=422, detail="Una medición de pre-siembra no puede ser posterior a la fecha prevista de siembra.")

    nuevo = MedicionBiofloc(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {str(e)}")

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {
        "lote_id": data.lote_id,
        "volumen_sedimentable": float(data.volumen_sedimentable),
        "relacion_cn": float(data.relacion_cn) if data.relacion_cn is not None else None,
    })
    db.commit()
    db.refresh(nuevo)
    return nuevo
