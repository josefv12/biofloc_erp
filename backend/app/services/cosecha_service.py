"""
Servicio para operaciones CRUD de cosechas.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La fecha no puede ser anterior a la fecha_siembra del lote.
- peso_total_kg y cantidad_peces deben ser > 0 (validadas en Pydantic y DB CHECK).
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.cosecha import Cosecha
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.cosecha import CosechaCreate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="cosechas",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_cosechas(db: Session, lote_id: int | None = None) -> list[Cosecha]:
    q = db.query(Cosecha)
    if lote_id:
        q = q.filter(Cosecha.lote_id == lote_id)
    return q.order_by(Cosecha.fecha_hora.desc()).all()


def obtener_cosecha(db: Session, cosecha_id: int) -> Cosecha:
    c = db.query(Cosecha).filter(Cosecha.id == cosecha_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cosecha no encontrada")
    return c


def crear_cosecha(db: Session, data: CosechaCreate, usuario_id: int) -> Cosecha:
    # Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    
    # Validar fecha_hora contra fecha_siembra
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la cosecha no puede ser anterior a la siembra del lote")

    nuevo = Cosecha(**data.model_dump(), registrado_por=usuario_id)
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
            "cantidad_peces": data.cantidad_peces, 
            "peso_total_kg": float(data.peso_total_kg),
            "peso_promedio_g": float(data.peso_promedio_g) if data.peso_promedio_g is not None else None
        }
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
