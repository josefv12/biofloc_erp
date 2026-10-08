"""
Servicio para mediciones de agua en lotes activos o estanques en pre-siembra.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_agua import MedicionAgua
from app.models.lote import Lote
from app.models.estanque import Estanque
from app.models.parametro_agua import ParametroAgua
from app.models.auditoria import Auditoria
from app.schemas.medicion_agua import MedicionAguaCreate
from app.services.poblacion_lote import exigir_lote_en_produccion
from app.services.validaciones_temporales import validar_evento_lote, validar_evento_no_futuro


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_agua",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    ))


def listar_mediciones_agua(
    db: Session,
    lote_id: int | None = None,
    estanque_id: int | None = None,
    parametro_id: int | None = None,
) -> list[MedicionAgua]:
    q = db.query(MedicionAgua)
    if lote_id:
        q = q.filter(MedicionAgua.lote_id == lote_id)
    if estanque_id:
        q = q.filter(MedicionAgua.estanque_id == estanque_id)
    if parametro_id:
        q = q.filter(MedicionAgua.parametro_id == parametro_id)
    return q.order_by(MedicionAgua.fecha_hora.desc()).all()


def obtener_medicion_agua(db: Session, medicion_id: int) -> MedicionAgua:
    m = db.query(MedicionAgua).filter(MedicionAgua.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de agua no encontrada")
    return m


def crear_medicion_agua(db: Session, data: MedicionAguaCreate, usuario_id: int) -> MedicionAgua:
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
        validar_evento_lote(data.fecha_hora, lote.fecha_siembra, "la medición de agua")
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
        validar_evento_no_futuro(data.fecha_hora, "la medición de agua del estanque")

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

    _registrar_auditoria(
        db, usuario_id, "INSERT", nuevo.id,
        {
            "lote_id": data.lote_id,
            "estanque_id": data.estanque_id,
            "parametro_id": data.parametro_id,
            "valor": float(data.valor),
        },
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
