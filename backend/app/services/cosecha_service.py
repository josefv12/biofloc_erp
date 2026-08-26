"""
Servicio para operaciones CRUD de cosechas.

Reglas de negocio aplicadas:
- lote_id debe existir y estar ACTIVO.
- La fecha no puede ser anterior a la fecha_siembra del lote.
- peso_total_kg y cantidad_peces deben ser > 0 (validadas en Pydantic y DB CHECK).
- La nueva cosecha no puede superar la población disponible
  (sembrados − mortalidad acumulada − cosecha previa).
- Si el cliente no envía peso_promedio_g, se calcula con peso_total_kg × 1000 / cantidad.
- Si tras registrar la cosecha la población disponible es 0, el lote pasa a FINALIZADO
  (estado existente) y se asigna fecha_cierre si estaba vacía.
- La auditoría registra INSERT de cosecha y, si aplica, UPDATE del lote.
- No se expone UPDATE ni DELETE.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.cosecha import Cosecha
from app.models.lote import Lote
from app.models.auditoria import Auditoria
from app.schemas.cosecha import CosechaCreate
from app.services.poblacion_lote import (
    ESTADO_LOTE_FINALIZADO,
    exigir_dentro_de_disponible,
    exigir_lote_en_produccion,
    mensaje_cosecha_excede,
    obtener_estado_lote_por_nombre,
    obtener_poblacion_disponible,
)


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="cosechas",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def _peso_promedio_g(peso_total_kg: Decimal, cantidad_peces: int) -> Decimal | None:
    if cantidad_peces <= 0:
        return None
    return (peso_total_kg * Decimal("1000") / Decimal(cantidad_peces)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )


def _cerrar_lote_si_sin_peces(
    db: Session, lote: Lote, usuario_id: int, fecha_hora: datetime
) -> None:
    estado_fin = obtener_estado_lote_por_nombre(db, ESTADO_LOTE_FINALIZADO)
    if lote.estado_id == estado_fin.id:
        return
    lote.estado_id = estado_fin.id
    if lote.fecha_cierre is None:
        lote.fecha_cierre = fecha_hora.date()
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="lotes",
            registro_id=lote.id,
            accion="UPDATE",
            detalle={
                "estado": ESTADO_LOTE_FINALIZADO,
                "fecha_cierre": lote.fecha_cierre.isoformat() if lote.fecha_cierre else None,
                "origen": "cosecha_poblacion_cero",
            },
        )
    )


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
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")

    exigir_lote_en_produccion(db, lote)

    if data.fecha_hora.date() < lote.fecha_siembra:
        raise HTTPException(
            status_code=422,
            detail="La fecha de la cosecha no puede ser anterior a la siembra del lote",
        )

    disponible = obtener_poblacion_disponible(db, data.lote_id, lote.cantidad_sembrada)
    exigir_dentro_de_disponible(
        data.cantidad_peces,
        disponible,
        mensaje_cosecha_excede(data.cantidad_peces, disponible),
    )

    payload = data.model_dump()
    if payload.get("peso_promedio_g") is None:
        payload["peso_promedio_g"] = _peso_promedio_g(data.peso_total_kg, data.cantidad_peces)

    nuevo = Cosecha(**payload, registrado_por=usuario_id)
    db.add(nuevo)
    try:
        db.flush()
        restante = obtener_poblacion_disponible(db, data.lote_id, lote.cantidad_sembrada)
        if restante == 0:
            _cerrar_lote_si_sin_peces(db, lote, usuario_id, data.fecha_hora)
        _registrar_auditoria(
            db,
            usuario_id,
            "INSERT",
            nuevo.id,
            {
                "lote_id": data.lote_id,
                "cantidad_peces": data.cantidad_peces,
                "peso_total_kg": float(data.peso_total_kg),
                "peso_promedio_g": float(payload["peso_promedio_g"])
                if payload.get("peso_promedio_g") is not None
                else None,
                "poblacion_restante": restante,
            },
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
