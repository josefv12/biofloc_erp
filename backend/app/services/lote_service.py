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
from sqlalchemy.exc import IntegrityError, InternalError
from fastapi import HTTPException

from app.models.lote import Lote, Especie, EtapaProductiva, EstadoLote
from app.models.estanque import Estanque
from app.models.auditoria import Auditoria
from app.schemas.lote import LoteCreate, LoteUpdate
from app.services.validaciones_fecha import validar_fecha_no_futura


def _verificar_referencias(db: Session, data: LoteCreate | LoteUpdate) -> None:
    if hasattr(data, "estanque_id") and data.estanque_id is not None:
        est = db.query(Estanque).filter(Estanque.id == data.estanque_id, Estanque.activo == True).first()
        if not est:
            raise HTTPException(status_code=404, detail=f"Estanque id={data.estanque_id} no existe o está inactivo")

    if hasattr(data, "especie_id") and data.especie_id is not None:
        especie = db.query(Especie).filter(Especie.id == data.especie_id).first()
        if not especie:
            raise HTTPException(status_code=404, detail=f"Especie id={data.especie_id} no existe")
        if not especie.activo:
            raise HTTPException(status_code=422, detail=f"Especie id={data.especie_id} está inactiva")

    if hasattr(data, "etapa_productiva_id") and data.etapa_productiva_id is not None:
        etapa = db.query(EtapaProductiva).filter(EtapaProductiva.id == data.etapa_productiva_id).first()
        if not etapa:
            raise HTTPException(status_code=404, detail=f"EtapaProductiva id={data.etapa_productiva_id} no existe")
        if not etapa.activo:
            raise HTTPException(status_code=422, detail=f"EtapaProductiva id={data.etapa_productiva_id} está inactiva")

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
    if activos:
        q = q.join(EstadoLote, Lote.estado_id == EstadoLote.id).filter(EstadoLote.nombre == "ACTIVO")
    return q.order_by(Lote.id.desc()).all()


def obtener_lote(db: Session, lote_id: int) -> Lote:
    lote = db.query(Lote).filter(Lote.id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


def _validar_estanque_operativo_para_lote(db: Session, estanque_id: int, estado_id: int) -> None:
    estado_lote = db.query(EstadoLote).filter(EstadoLote.id == estado_id).first()
    if not estado_lote:
        raise HTTPException(status_code=404, detail=f"EstadoLote id={estado_id} no existe")

    if estado_lote.nombre != "ACTIVO":
        return

    est = db.query(Estanque).filter(Estanque.id == estanque_id, Estanque.activo == True).first()
    if not est:
        raise HTTPException(status_code=404, detail=f"Estanque id={estanque_id} no existe o está inactivo")

    estado_estanque = est.estado
    if estado_estanque and estado_estanque.nombre != "OCUPADO":
        raise HTTPException(
            status_code=422,
            detail=f"Un lote ACTIVO solo puede ocupar un estanque en estado OCUPADO; estado actual: {estado_estanque.nombre}",
        )


def crear_lote(db: Session, data: LoteCreate, usuario_id: int) -> Lote:
    validar_fecha_no_futura(data.fecha_siembra, "La fecha de siembra")
    _verificar_referencias(db, data)
    _validar_estanque_operativo_para_lote(db, data.estanque_id, data.estado_id)

    # Verificar código único
    if db.query(Lote).filter(Lote.codigo == data.codigo).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un lote con código '{data.codigo}'")

    nuevo = Lote(**data.model_dump())
    db.add(nuevo)
    try:
        db.flush()
    except (IntegrityError, InternalError) as exc:
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

    if data.fecha_cierre is not None:
        # Un cierre no puede quedar antes de un evento histórico ya registrado.
        from sqlalchemy import text
        ultimo = db.execute(
            text("""
                SELECT MAX(fecha_evento) FROM (
                    SELECT fecha_hora AS fecha_evento FROM biofloc.biometrias WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.mortalidades WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.cosechas WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.alimentaciones WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.mediciones_biofloc WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.mediciones_agua WHERE lote_id = :lote_id
                    UNION ALL SELECT fecha_hora FROM biofloc.aplicaciones_biofloc WHERE lote_id = :lote_id
                ) eventos
            """),
            {"lote_id": lote.id},
        ).scalar()
        if ultimo is not None and ultimo.date() > data.fecha_cierre:
            raise HTTPException(
                status_code=422,
                detail="fecha_cierre no puede ser anterior a un evento histórico del lote",
            )

    cambios = data.model_dump(exclude_none=True)

    estado_id_nuevo = cambios.get("estado_id", lote.estado_id)
    estanque_id_nuevo = cambios.get("estanque_id", lote.estanque_id)
    estado_nuevo = db.query(EstadoLote).filter(EstadoLote.id == estado_id_nuevo).first()
    if not estado_nuevo:
        raise HTTPException(status_code=404, detail=f"EstadoLote id={estado_id_nuevo} no existe")
    if not estado_nuevo.activo:
        raise HTTPException(status_code=422, detail=f"EstadoLote id={estado_id_nuevo} está inactivo")

    estados_terminales = {"FINALIZADO", "CANCELADO"}
    if estado_nuevo.nombre in estados_terminales and "fecha_cierre" not in cambios and lote.fecha_cierre is None:
        raise HTTPException(
            status_code=422,
            detail=f"El estado {estado_nuevo.nombre} requiere fecha_cierre",
        )
    if estado_nuevo.nombre == "ACTIVO" and (cambios.get("fecha_cierre", lote.fecha_cierre) is not None):
        raise HTTPException(status_code=422, detail="Un lote ACTIVO no puede tener fecha_cierre")
    _validar_estanque_operativo_para_lote(db, estanque_id_nuevo, estado_nuevo.id)
    if lote.estado and lote.estado.nombre in estados_terminales and estado_nuevo.nombre != lote.estado.nombre:
        raise HTTPException(status_code=422, detail="Un lote FINALIZADO o CANCELADO no puede reabrirse ni cambiar de estado")

    for campo, valor in cambios.items():
        setattr(lote, campo, valor)

    # auditoria.detalle es JSONB: fecha_cierre (date) no es serializable directamente.
    detalle = data.model_dump(exclude_none=True, mode="json")

    try:
        db.flush()
    except (IntegrityError, InternalError) as exc:
        db.rollback()
        if "ya tiene un lote activo" in str(exc.orig).lower():
            raise HTTPException(status_code=409, detail="El estanque ya tiene un lote ACTIVO")
        raise HTTPException(status_code=409, detail=f"Conflicto de integridad: {exc.orig}")

    _registrar_auditoria(db, usuario_id, "UPDATE", lote.id, detalle)
    db.commit()
    db.refresh(lote)
    return lote
