"""
Servicio para mediciones de Biofloc en lotes activos o estanques en pre-siembra.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_biofloc import MedicionBiofloc
from app.models.lote import Lote
from app.models.estanque import Estanque
from app.models.auditoria import Auditoria
from app.schemas.medicion_biofloc import MedicionBioflocCreate
from app.services.poblacion_lote import exigir_lote_en_produccion
from app.services.validaciones_temporales import validar_evento_lote, validar_evento_no_futuro


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    ))


def listar_mediciones_biofloc(
    db: Session,
    lote_id: int | None = None,
    estanque_id: int | None = None,
) -> list[MedicionBiofloc]:
    q = db.query(MedicionBiofloc)
    if lote_id:
        q = q.filter(MedicionBiofloc.lote_id == lote_id)
    if estanque_id:
        q = q.filter(MedicionBiofloc.estanque_id == estanque_id)
    return q.order_by(MedicionBiofloc.fecha_hora.desc()).all()


def obtener_medicion_biofloc(db: Session, medicion_id: int) -> MedicionBiofloc:
    m = db.query(MedicionBiofloc).filter(MedicionBiofloc.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de Biofloc no encontrada")
    return m


def crear_medicion_biofloc(db: Session, data: MedicionBioflocCreate, usuario_id: int) -> MedicionBiofloc:
    if (data.lote_id is None) == (data.estanque_id is None):
        raise HTTPException(
            status_code=422,
            detail="La medición debe estar asociada a un lote activo o a un estanque en pre-siembra.",
        )

    if data.lote_id is not None:
        lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
        if not lote:
            raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
        exigir_lote_en_produccion(db, lote)
        validar_evento_lote(data.fecha_hora, lote.fecha_siembra, "la medición de Biofloc")
    else:
        estanque = db.query(Estanque).filter(Estanque.id == data.estanque_id).first()
        if not estanque:
            raise HTTPException(status_code=404, detail=f"Estanque id={data.estanque_id} no existe")
        lote_activo = (
            db.query(Lote)
            .filter(Lote.estanque_id == estanque.id)
            .join(Lote.estado)
            .filter_by(nombre="ACTIVO")
            .first()
        )
        if lote_activo:
            raise HTTPException(
                status_code=422,
                detail="El estanque tiene un lote ACTIVO. Registre la medición desde el lote.",
            )
        validar_evento_no_futuro(data.fecha_hora, "la medición de Biofloc del estanque")

    if data.volumen_sedimentable < 0:
        raise HTTPException(status_code=422, detail="El volumen sedimentable debe ser mayor o igual a 0")
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
        db, usuario_id, "INSERT", nuevo.id,
        {
            "lote_id": data.lote_id,
            "estanque_id": data.estanque_id,
            "volumen_sedimentable": float(data.volumen_sedimentable),
            "relacion_cn": float(data.relacion_cn) if data.relacion_cn is not None else None,
        },
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
