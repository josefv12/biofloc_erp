"""
Servicio para operaciones CRUD del catálogo parametros_agua.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.parametro_agua import ParametroAgua
from app.models.auditoria import Auditoria
from app.schemas.parametro_agua import ParametroAguaCreate, ParametroAguaUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="parametros_agua",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_parametros_agua(db: Session, solo_activos: bool = False) -> list[ParametroAgua]:
    q = db.query(ParametroAgua)
    if solo_activos:
        q = q.filter(ParametroAgua.activo == True)
    return q.order_by(ParametroAgua.nombre.asc()).all()


def obtener_parametro_agua(db: Session, parametro_id: int) -> ParametroAgua:
    p = db.query(ParametroAgua).filter(ParametroAgua.id == parametro_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parámetro de agua no encontrado")
    return p


def crear_parametro_agua(db: Session, data: ParametroAguaCreate, usuario_id: int) -> ParametroAgua:
    # Verificar duplicado de nombre
    existente = db.query(ParametroAgua).filter(ParametroAgua.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un parámetro de agua con el nombre '{data.nombre}'")

    nuevo = ParametroAgua(**data.model_dump())
    db.add(nuevo)
    
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar el parámetro de agua")

    _registrar_auditoria(
        db, 
        usuario_id, 
        "INSERT", 
        nuevo.id, 
        {"nombre": nuevo.nombre, "unidad": nuevo.unidad, "activo": nuevo.activo}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_parametro_agua(db: Session, parametro_id: int, data: ParametroAguaUpdate, usuario_id: int) -> ParametroAgua:
    p = obtener_parametro_agua(db, parametro_id)
    
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return p

    if "nombre" in cambios and cambios["nombre"] != p.nombre:
        existente = db.query(ParametroAgua).filter(ParametroAgua.nombre == cambios["nombre"]).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe otro parámetro de agua con el nombre '{cambios['nombre']}'")

    for key, value in cambios.items():
        setattr(p, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar el parámetro de agua")

    _registrar_auditoria(
        db,
        usuario_id,
        "UPDATE",
        p.id,
        cambios
    )
    db.commit()
    db.refresh(p)
    return p
