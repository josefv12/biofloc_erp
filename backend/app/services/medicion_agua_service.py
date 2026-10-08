"""
Servicio para mediciones de agua asociadas al ciclo productivo (lote).
El lote puede estar PLANIFICADO (pre-siembra) o ACTIVO (producción).
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_agua import MedicionAgua
from app.models.lote import Lote
from app.models.parametro_agua import ParametroAgua
from app.models.auditoria import Auditoria
from app.schemas.medicion_agua import MedicionAguaCreate
from app.services.validaciones_temporales import validar_evento_lote, validar_evento_no_futuro

ESTADOS_MEDICION_PERMITIDOS = {"PLANIFICADO", "ACTIVO"}

def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_agua",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    ))

def listar_mediciones_agua(db: Session, lote_id: int | None = None, parametro_id: int | None = None) -> list[MedicionAgua]:
    q = db.query(MedicionAgua)
    if lote_id is not None:
        q = q.filter(MedicionAgua.lote_id == lote_id)
    if parametro_id is not None:
        q = q.filter(MedicionAgua.parametro_id == parametro_id)
    return q.order_by(MedicionAgua.fecha_hora.desc()).all()

def obtener_medicion_agua(db: Session, medicion_id: int) -> MedicionAgua:
    m = db.query(MedicionAgua).filter(MedicionAgua.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de agua no encontrada")
    return m

def crear_medicion_agua(db: Session, data: MedicionAguaCreate, usuario_id: int) -> MedicionAgua:
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")

    if lote.estado.nombre not in ESTADOS_MEDICION_PERMITIDOS:
        raise HTTPException(status_code=422, detail="Solo se pueden registrar mediciones para lotes PLANIFICADOS o ACTIVOS.")

    validar_evento_no_futuro(data.fecha_hora, "la medición de agua")
    if lote.estado.nombre == "ACTIVO":
        validar_evento_lote(data.fecha_hora, lote.fecha_siembra, "la medición de agua")
    else:
        if data.fecha_hora.date() > lote.fecha_siembra:
            raise HTTPException(status_code=422, detail="Una medición de pre-siembra no puede ser posterior a la fecha prevista de siembra.")

    parametro = db.query(ParametroAgua).filter(ParametroAgua.id == data.parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail=f"Parámetro de agua id={data.parametro_id} no existe")

    nuevo = MedicionAgua(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {str(e)}")

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {
        "lote_id": data.lote_id,
        "parametro_id": data.parametro_id,
        "valor": float(data.valor),
    })
    db.commit()
    db.refresh(nuevo)
    return nuevo
