"""
Servicio para operaciones CRUD del catálogo referencias_agua.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.referencia_agua import ReferenciaAgua
from app.models.parametro_agua import ParametroAgua
from app.models.lote import Especie, EtapaProductiva
from app.models.auditoria import Auditoria
from app.schemas.referencia_agua import ReferenciaAguaCreate, ReferenciaAguaUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="referencias_agua",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_referencias_agua(
    db: Session,
    especie_id: int | None = None,
    etapa_productiva_id: int | None = None,
    parametro_id: int | None = None,
    solo_activos: bool = False
) -> list[ReferenciaAgua]:
    q = db.query(ReferenciaAgua)
    if especie_id:
        q = q.filter(ReferenciaAgua.especie_id == especie_id)
    if etapa_productiva_id:
        q = q.filter(ReferenciaAgua.etapa_productiva_id == etapa_productiva_id)
    if parametro_id:
        q = q.filter(ReferenciaAgua.parametro_id == parametro_id)
    if solo_activos:
        q = q.filter(ReferenciaAgua.activo == True)
    return q.order_by(ReferenciaAgua.id.asc()).all()


def obtener_referencia_agua(db: Session, referencia_id: int) -> ReferenciaAgua:
    r = db.query(ReferenciaAgua).filter(ReferenciaAgua.id == referencia_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Referencia de agua no encontrada")
    return r


def crear_referencia_agua(db: Session, data: ReferenciaAguaCreate, usuario_id: int) -> ReferenciaAgua:
    # 1. Validar especie_id
    especie = db.query(Especie).filter(Especie.id == data.especie_id).first()
    if not especie:
        raise HTTPException(status_code=404, detail=f"Especie id={data.especie_id} no existe")

    # 2. Validar etapa_productiva_id
    etapa = db.query(EtapaProductiva).filter(EtapaProductiva.id == data.etapa_productiva_id).first()
    if not etapa:
        raise HTTPException(status_code=404, detail=f"Etapa productiva id={data.etapa_productiva_id} no existe")

    # 3. Validar parametro_id
    parametro = db.query(ParametroAgua).filter(ParametroAgua.id == data.parametro_id).first()
    if not parametro:
        raise HTTPException(status_code=404, detail=f"Parámetro de agua id={data.parametro_id} no existe")

    # 4. Validar unicidad (especie, etapa, parametro)
    existente = db.query(ReferenciaAgua).filter(
        ReferenciaAgua.especie_id == data.especie_id,
        ReferenciaAgua.etapa_productiva_id == data.etapa_productiva_id,
        ReferenciaAgua.parametro_id == data.parametro_id
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una referencia de agua configurada para esta combinación de Especie, Etapa Productiva y Parámetro"
        )

    # 5. Validar rangos
    if data.valor_minimo is not None and data.valor_maximo is not None:
        if data.valor_minimo > data.valor_maximo:
            raise HTTPException(status_code=422, detail="valor_minimo no puede ser mayor que valor_maximo")

    nuevo = ReferenciaAgua(**data.model_dump())
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad al registrar la referencia de agua: {str(e)}")

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {
            "especie_id": nuevo.especie_id,
            "etapa_productiva_id": nuevo.etapa_productiva_id,
            "parametro_id": nuevo.parametro_id,
            "valor_minimo": float(nuevo.valor_minimo) if nuevo.valor_minimo is not None else None,
            "valor_maximo": float(nuevo.valor_maximo) if nuevo.valor_maximo is not None else None,
        }
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_referencia_agua(db: Session, referencia_id: int, data: ReferenciaAguaUpdate, usuario_id: int) -> ReferenciaAgua:
    r = obtener_referencia_agua(db, referencia_id)

    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return r

    # Evaluar combinación de valores nuevos y existentes para la validación del rango
    nuevo_min = cambios.get("valor_minimo", r.valor_minimo)
    nuevo_max = cambios.get("valor_maximo", r.valor_maximo)

    if nuevo_min is not None and nuevo_max is not None:
        if nuevo_min > nuevo_max:
            raise HTTPException(status_code=422, detail="valor_minimo no puede ser mayor que valor_maximo")

    for key, value in cambios.items():
        setattr(r, key, value)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad al actualizar la referencia de agua: {str(e)}")

    # Convertir Decimal a float para serialización JSONB en auditoría
    detalle_auditoria = {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in cambios.items()
    }

    _registrar_auditoria(
        db,
        usuario_id,
        "UPDATE",
        r.id,
        detalle_auditoria
    )
    db.commit()
    db.refresh(r)
    return r
