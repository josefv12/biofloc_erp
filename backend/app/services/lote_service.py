"""
Servicio para operaciones CRUD de lotes.

Reglas de negocio aplicadas:
- estanque_id debe existir y estar activo.
- especie_id, etapa_productiva_id, estado_id deben existir en sus catálogos.
- La validación de 1 solo lote ACTIVO por estanque está delegada al trigger
  PostgreSQL (trg_validar_lote_activo). Si viola la restricción, PostgreSQL
  lanza una excepción que el servicio convierte en HTTP 409.
- fecha_cierre >= fecha_siembra (también en el CHECK del schema).
- No se aplica DELETE físico; el estado CANCELADO/FINALIZADO cierra el lote.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.lote import Lote, Especie, EtapaProductiva, EstadoLote
from app.models.estanque import Estanque
from app.models.auditoria import Auditoria
from app.schemas.lote import LoteCreate, LoteUpdate


def _verificar_referencias(db: Session, data: LoteCreate | LoteUpdate) -> None:
    if hasattr(data, "estanque_id") and data.estanque_id is not None:
        est = db.query(Estanque).filter(Estanque.id == data.estanque_id, Estanque.activo == True).first()
        if not est:
            raise HTTPException(status_code=404, detail=f"Estanque id={data.estanque_id} no existe o está inactivo")

    if hasattr(data, "especie_id") and data.especie_id is not None:
        if not db.query(Especie).filter(Especie.id == data.especie_id).first():
            raise HTTPException(status_code=404, detail=f"Especie id={data.especie_id} no existe")

    if hasattr(data, "etapa_productiva_id") and data.etapa_productiva_id is not None:
        if not db.query(EtapaProductiva).filter(EtapaProductiva.id == data.etapa_productiva_id).first():
            raise HTTPException(status_code=404, detail=f"EtapaProductiva id={data.etapa_productiva_id} no existe")

    if hasattr(data, "estado_id") and data.estado_id is not None:
        if not db.query(EstadoLote).filter(EstadoLote.id == data.estado_id).first():
            raise HTTPException(status_code=404, detail=f"EstadoLote id={data.estado_id} no existe")


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="lotes",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_lotes(db: Session, estanque_id: int | None = None, activos: bool = True) -> list[Lote]:
    q = db.query(Lote)
    if estanque_id:
        q = q.filter(Lote.estanque_id == estanque_id)
    return q.order_by(Lote.id.desc()).all()


def obtener_lote(db: Session, lote_id: int) -> Lote:
    lote = db.query(Lote).filter(Lote.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


def crear_lote(db: Session, data: LoteCreate, usuario_id: int) -> Lote:
    _verificar_referencias(db, data)

    # Verificar código único
    if db.query(Lote).filter(Lote.codigo == data.codigo).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un lote con código '{data.codigo}'")

    nuevo = Lote(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        # El trigger de PostgreSQL puede lanzar excepción sobre lote activo duplicado
        if "ya tiene un lote activo" in str(exc.orig).lower() or "lote activo" in str(exc.orig).lower():
            raise HTTPException(status_code=409, detail="El estanque ya tiene un lote ACTIVO")
        raise HTTPException(status_code=409, detail=f"Conflicto de integridad: {exc.orig}")

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {"codigo": data.codigo, "estanque_id": data.estanque_id})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_lote(db: Session, lote_id: int, data: LoteUpdate, usuario_id: int) -> Lote:
    lote = obtener_lote(db, lote_id)
    _verificar_referencias(db, data)

    # Validar fecha_cierre contra fecha_siembra existente
    if data.fecha_cierre and data.fecha_cierre < lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="fecha_cierre debe ser >= fecha_siembra")

    cambios = data.model_dump(exclude_none=True)
    for campo, valor in cambios.items():
        setattr(lote, campo, valor)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if "ya tiene un lote activo" in str(exc.orig).lower():
            raise HTTPException(status_code=409, detail="El estanque ya tiene un lote ACTIVO")
        raise HTTPException(status_code=409, detail=f"Conflicto de integridad: {exc.orig}")

    _registrar_auditoria(db, usuario_id, "UPDATE", lote.id, cambios)
    db.commit()
    db.refresh(lote)
    return lote
