"""
Servicio para operaciones CRUD del catálogo tipos_aplicacion_biofloc.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.tipo_aplicacion_biofloc import TipoAplicacionBiofloc
from app.models.auditoria import Auditoria
from app.schemas.tipo_aplicacion_biofloc import TipoAplicacionBioflocCreate, TipoAplicacionBioflocUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="tipos_aplicacion_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_tipos_aplicacion_biofloc(db: Session, solo_activos: bool = False) -> list[TipoAplicacionBiofloc]:
    q = db.query(TipoAplicacionBiofloc)
    if solo_activos:
        q = q.filter(TipoAplicacionBiofloc.activo == True)
    return q.order_by(TipoAplicacionBiofloc.nombre.asc()).all()


def obtener_tipo_aplicacion_biofloc(db: Session, tipo_id: int) -> TipoAplicacionBiofloc:
    t = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tipo de aplicación Biofloc no encontrado")
    return t


def crear_tipo_aplicacion_biofloc(db: Session, data: TipoAplicacionBioflocCreate, usuario_id: int) -> TipoAplicacionBiofloc:
    existente = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un tipo de aplicación Biofloc con el nombre '{data.nombre}'")

    nuevo = TipoAplicacionBiofloc(**data.model_dump())
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al registrar el tipo de aplicación Biofloc")

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {"nombre": nuevo.nombre, "activo": nuevo.activo}
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_tipo_aplicacion_biofloc(db: Session, tipo_id: int, data: TipoAplicacionBioflocUpdate, usuario_id: int) -> TipoAplicacionBiofloc:
    t = obtener_tipo_aplicacion_biofloc(db, tipo_id)

    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return t

    if "nombre" in cambios and cambios["nombre"] != t.nombre:
        existente = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.nombre == cambios["nombre"]).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe otro tipo de aplicación Biofloc con el nombre '{cambios['nombre']}'")

    for key, value in cambios.items():
        setattr(t, key, value)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar el tipo de aplicación Biofloc")

    _registrar_auditoria(
        db,
        usuario_id,
        "UPDATE",
        t.id,
        cambios
    )
    db.commit()
    db.refresh(t)
    return t
