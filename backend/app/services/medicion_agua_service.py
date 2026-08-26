"""
Servicio para operaciones CRUD de mediciones_agua.

Reglas de negocio aplicadas:
- lote_id debe existir.
- parametro_id debe existir.
- La fecha no puede ser anterior a la fecha_siembra del lote.
- valor debe ser >= 0 (validadas en Pydantic y DB CHECK).
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.medicion_agua import MedicionAgua
from app.models.lote import Lote
from app.models.parametro_agua import ParametroAgua
from app.models.auditoria import Auditoria
from app.schemas.medicion_agua import MedicionAguaCreate
from app.services.poblacion_lote import exigir_lote_en_produccion


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="mediciones_agua",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_mediciones_agua(
    db: Session,
    lote_id: int | None = None,
    parametro_id: int | None = None
) -> list[MedicionAgua]:
    q = db.query(MedicionAgua)
    if lote_id:
        q = q.filter(MedicionAgua.lote_id == lote_id)
    if parametro_id:
        q = q.filter(MedicionAgua.parametro_id == parametro_id)
    return q.order_by(MedicionAgua.fecha_hora.desc()).all()


def obtener_medicion_agua(db: Session, medicion_id: int) -> MedicionAgua:
    m = db.query(MedicionAgua).filter(MedicionAgua.id == medicion_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medición de agua no encontrada")
    return m


def crear_medicion_agua(db: Session, data: MedicionAguaCreate, usuario_id: int) -> MedicionAgua:
    # 1. Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    exigir_lote_en_produccion(db, lote)

    # 2. Validar parametro_id
    parametro = db.query(ParametroAgua).filter(ParametroAgua.id == data.parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail=f"Parámetro de agua id={data.parametro_id} no existe")

    # 3. Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la medición de agua no puede ser anterior a la siembra del lote")

    # 4. Validar valor >= 0
    if data.valor < 0:
        raise HTTPException(status_code=422, detail="El valor de la medición de agua debe ser mayor o igual a 0")

    nuevo = MedicionAgua(**data.model_dump(), registrado_por=usuario_id)
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
            "parametro_id": data.parametro_id,
            "valor": float(data.valor)
        }
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
