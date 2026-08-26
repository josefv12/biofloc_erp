"""
Servicio para operaciones CRUD de mortalidades.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE porque el schema no contempla edición (no hay updated_at).
- La nueva mortalidad no puede superar la población disponible
  (sembrados − mortalidad previa − cosecha previa).
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.mortalidad import Mortalidad
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.mortalidad import MortalidadCreate
from app.services.poblacion_lote import (
    exigir_dentro_de_disponible,
    exigir_lote_en_produccion,
    mensaje_mortalidad_excede,
    obtener_poblacion_disponible,
)


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="mortalidades",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_mortalidades(db: Session, lote_id: int | None = None) -> list[Mortalidad]:
    q = db.query(Mortalidad)
    if lote_id:
        q = q.filter(Mortalidad.lote_id == lote_id)
    return q.order_by(Mortalidad.fecha_hora.desc()).all()


def obtener_mortalidad(db: Session, mortalidad_id: int) -> Mortalidad:
    m = db.query(Mortalidad).filter(Mortalidad.id == mortalidad_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mortalidad no encontrada")
    return m


def crear_mortalidad(db: Session, data: MortalidadCreate, usuario_id: int) -> Mortalidad:
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    exigir_lote_en_produccion(db, lote)

    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(
            status_code=422,
            detail="La fecha de la mortalidad no puede ser anterior a la siembra del lote",
        )

    disponible = obtener_poblacion_disponible(db, data.lote_id, lote.cantidad_sembrada)
    exigir_dentro_de_disponible(
        data.cantidad,
        disponible,
        mensaje_mortalidad_excede(data.cantidad, disponible),
    )

    nuevo = Mortalidad(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)
    try:
        db.flush()
        _registrar_auditoria(
            db,
            usuario_id,
            "INSERT",
            nuevo.id,
            {"lote_id": data.lote_id, "cantidad": data.cantidad, "causa": data.causa},
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad en base de datos")
    except Exception:
        db.rollback()
        raise

    db.refresh(nuevo)
    return nuevo
