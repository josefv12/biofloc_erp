"""CRUD de referencias Biofloc. Sin valores semilla; el administrador digita los rangos."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.lote import Especie, EtapaProductiva
from app.models.referencia_biofloc import INDICADORES_BIOFLOC, ReferenciaBiofloc
from app.schemas.referencia_biofloc import ReferenciaBioflocCreate, ReferenciaBioflocUpdate


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="referencias_biofloc",
            registro_id=registro_id,
            accion=accion,
            detalle=detalle,
        )
    )


def _serializar(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def listar_referencias_biofloc(
    db: Session,
    especie_id: int | None = None,
    etapa_productiva_id: int | None = None,
    indicador: str | None = None,
    solo_activos: bool = False,
) -> list[ReferenciaBiofloc]:
    q = db.query(ReferenciaBiofloc)
    if especie_id:
        q = q.filter(ReferenciaBiofloc.especie_id == especie_id)
    if etapa_productiva_id:
        q = q.filter(ReferenciaBiofloc.etapa_productiva_id == etapa_productiva_id)
    if indicador:
        q = q.filter(ReferenciaBiofloc.indicador == indicador.strip().upper())
    if solo_activos:
        q = q.filter(ReferenciaBiofloc.activo.is_(True))
    return q.order_by(ReferenciaBiofloc.id.asc()).all()


def obtener_referencia_biofloc(db: Session, referencia_id: int) -> ReferenciaBiofloc:
    row = db.query(ReferenciaBiofloc).filter(ReferenciaBiofloc.id == referencia_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Referencia Biofloc no encontrada")
    return row


def crear_referencia_biofloc(
    db: Session, data: ReferenciaBioflocCreate, usuario_id: int
) -> ReferenciaBiofloc:
    if not db.query(Especie).filter(Especie.id == data.especie_id).first():
        raise HTTPException(status_code=404, detail=f"Especie id={data.especie_id} no existe")
    if not db.query(EtapaProductiva).filter(EtapaProductiva.id == data.etapa_productiva_id).first():
        raise HTTPException(
            status_code=404, detail=f"Etapa productiva id={data.etapa_productiva_id} no existe"
        )
    if data.indicador not in INDICADORES_BIOFLOC:
        raise HTTPException(status_code=422, detail="indicador no admitido")

    existente = (
        db.query(ReferenciaBiofloc)
        .filter(
            ReferenciaBiofloc.especie_id == data.especie_id,
            ReferenciaBiofloc.etapa_productiva_id == data.etapa_productiva_id,
            ReferenciaBiofloc.indicador == data.indicador,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una referencia Biofloc para esta especie, etapa e indicador",
        )

    nuevo = ReferenciaBiofloc(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad en referencia Biofloc")

    _registrar_auditoria(
        db,
        usuario_id,
        "INSERT",
        nuevo.id,
        {
            "especie_id": nuevo.especie_id,
            "etapa_productiva_id": nuevo.etapa_productiva_id,
            "indicador": nuevo.indicador,
            "valor_minimo": _serializar(nuevo.valor_minimo),
            "valor_objetivo": _serializar(nuevo.valor_objetivo),
            "valor_maximo": _serializar(nuevo.valor_maximo),
        },
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_referencia_biofloc(
    db: Session, referencia_id: int, data: ReferenciaBioflocUpdate, usuario_id: int
) -> ReferenciaBiofloc:
    row = obtener_referencia_biofloc(db, referencia_id)
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        return row

    nuevo_min = cambios.get("valor_minimo", row.valor_minimo)
    nuevo_max = cambios.get("valor_maximo", row.valor_maximo)
    nuevo_obj = cambios.get("valor_objetivo", row.valor_objetivo)
    if nuevo_min is not None and nuevo_max is not None and nuevo_min > nuevo_max:
        raise HTTPException(status_code=422, detail="valor_minimo no puede ser mayor que valor_maximo")
    if nuevo_obj is not None and nuevo_min is not None and nuevo_obj < nuevo_min:
        raise HTTPException(status_code=422, detail="valor_objetivo no puede ser menor que valor_minimo")
    if nuevo_obj is not None and nuevo_max is not None and nuevo_obj > nuevo_max:
        raise HTTPException(status_code=422, detail="valor_objetivo no puede ser mayor que valor_maximo")

    for key, value in cambios.items():
        setattr(row, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad al actualizar referencia Biofloc")

    _registrar_auditoria(
        db,
        usuario_id,
        "UPDATE",
        row.id,
        {k: _serializar(v) for k, v in cambios.items()},
    )
    db.commit()
    db.refresh(row)
    return row
