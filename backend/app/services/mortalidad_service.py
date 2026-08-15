"""
Servicio para operaciones CRUD de mortalidades.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE porque el schema no contempla edición (no hay updated_at).
- La mortalidad acumulada (incluyendo la nueva) no puede superar la población sembrada del lote.
"""
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi import HTTPException

from app.models.mortalidad import Mortalidad
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.mortalidad import MortalidadCreate


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
    # Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    
    # Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la mortalidad no puede ser anterior a la siembra del lote")

    # Validar población lógica (mortalidad_acumulada + nueva_cantidad <= cantidad_sembrada)
    mortalidad_acumulada = db.query(func.sum(Mortalidad.cantidad)).filter(Mortalidad.lote_id == data.lote_id).scalar() or 0
    if mortalidad_acumulada + data.cantidad > lote.cantidad_sembrada:
        raise HTTPException(
            status_code=422,
            detail=f"Mortalidad inválida: la población restante ({lote.cantidad_sembrada - mortalidad_acumulada}) es menor que la cantidad registrada ({data.cantidad})"
        )

    nuevo = Mortalidad(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)
    db.flush()

    _registrar_auditoria(
        db, 
        usuario_id, 
        "INSERT", 
        nuevo.id, 
        {"lote_id": data.lote_id, "cantidad": data.cantidad, "causa": data.causa}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
