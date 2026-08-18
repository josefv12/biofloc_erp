"""
Servicio para operaciones CRUD de biometrías.

Reglas de negocio aplicadas:
- lote_id debe existir.
- La auditoría registra INSERT en creación.
- No se expone UPDATE ni DELETE porque el schema no contempla edición (no hay updated_at).
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.biometria import Biometria
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.biometria import BiometriaCreate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="biometrias",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_biometrias(db: Session, lote_id: int | None = None) -> list[Biometria]:
    q = db.query(Biometria)
    if lote_id:
        q = q.filter(Biometria.lote_id == lote_id)
    return q.order_by(Biometria.fecha_hora.desc()).all()


def obtener_biometria(db: Session, biometria_id: int) -> Biometria:
    b = db.query(Biometria).filter(Biometria.id == biometria_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Biometría no encontrada")
    return b


def crear_biometria(db: Session, data: BiometriaCreate, usuario_id: int) -> Biometria:
    # Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    
    # Validar fecha_hora contra fecha_siembra
    # Although not explicitly in check constraints, logically biometria cannot happen before siembra.
    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La fecha de la biometría no puede ser anterior a la siembra del lote")

    nuevo = Biometria(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)
    db.flush()

    _registrar_auditoria(
        db, 
        usuario_id, 
        "INSERT", 
        nuevo.id, 
        {"lote_id": data.lote_id, "cantidad": data.cantidad_muestra, "peso_g": float(data.peso_total_muestra_g)}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo
