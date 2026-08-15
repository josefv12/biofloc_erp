"""
Servicio para operaciones CRUD del catálogo unidades.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.unidad import Unidad
from app.models.auditoria import Auditoria
from app.schemas.unidad import UnidadCreate, UnidadUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    detalle_safe = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in detalle.items()}
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="unidades",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle_safe,
    )
    db.add(entrada)


def listar_unidades(db: Session, solo_activos: bool = False) -> list[Unidad]:
    q = db.query(Unidad)
    if solo_activos:
        q = q.filter(Unidad.activo == True)
    return q.order_by(Unidad.nombre.asc()).all()


def obtener_unidad(db: Session, unidad_id: int) -> Unidad:
    u = db.query(Unidad).filter(Unidad.id == unidad_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    return u


def crear_unidad(db: Session, data: UnidadCreate, usuario_id: int) -> Unidad:
    ex_nombre = db.query(Unidad).filter(Unidad.nombre == data.nombre).first()
    if ex_nombre:
        raise HTTPException(status_code=409, detail=f"Ya existe una unidad con el nombre '{data.nombre}'")
    ex_simbolo = db.query(Unidad).filter(Unidad.simbolo == data.simbolo).first()
    if ex_simbolo:
        raise HTTPException(status_code=409, detail=f"Ya existe una unidad con el símbolo '{data.simbolo}'")

    nueva = Unidad(**data.model_dump())
    db.add(nueva)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar la unidad")

    _registrar_auditoria(db, usuario_id, "INSERT", nueva.id, {"nombre": nueva.nombre, "simbolo": nueva.simbolo, "activo": nueva.activo})
    db.commit()
    db.refresh(nueva)
    return nueva


def actualizar_unidad(db: Session, unidad_id: int, data: UnidadUpdate, usuario_id: int) -> Unidad:
    u = obtener_unidad(db, unidad_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return u

    if "nombre" in cambios and cambios["nombre"] != u.nombre:
        if db.query(Unidad).filter(Unidad.nombre == cambios["nombre"], Unidad.id != unidad_id).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otra unidad con el nombre '{cambios['nombre']}'")
    if "simbolo" in cambios and cambios["simbolo"] != u.simbolo:
        if db.query(Unidad).filter(Unidad.simbolo == cambios["simbolo"], Unidad.id != unidad_id).first():
            raise HTTPException(status_code=409, detail=f"Ya existe otra unidad con el símbolo '{cambios['simbolo']}'")

    for key, value in cambios.items():
        setattr(u, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar la unidad")

    _registrar_auditoria(db, usuario_id, "UPDATE", u.id, cambios)
    db.commit()
    db.refresh(u)
    return u
