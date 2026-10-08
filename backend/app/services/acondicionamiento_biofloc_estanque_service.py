from datetime import timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.acondicionamiento_biofloc_estanque import AcondicionamientoBioflocEstanque
from app.models.lote import Lote
from app.models.producto import Producto
from app.models.categoria_inventario import CategoriaInventario
from app.models.tipo_aplicacion_biofloc import TipoAplicacionBiofloc
from app.models.auditoria import Auditoria
from app.schemas.acondicionamiento_biofloc_estanque import AcondicionamientoBioflocEstanqueCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.movimiento_inventario_service import crear_movimiento_inventario, _obtener_tipo_salida_id
from app.services.validaciones_temporales import validar_evento_no_futuro

DIAS_ACONDICIONAMIENTO_BIOFLOC = 7

def _rol_tipo(tipo: TipoAplicacionBiofloc) -> str:
    return tipo.nombre.strip().upper()

def _validar_fecha(data: AcondicionamientoBioflocEstanqueCreate, lote: Lote) -> None:
    fecha_evento = data.fecha_hora.date()
    fecha_minima = lote.fecha_siembra - timedelta(days=DIAS_ACONDICIONAMIENTO_BIOFLOC)
    if fecha_evento < fecha_minima:
        raise HTTPException(
            status_code=422,
            detail=f"La aplicación no puede ser anterior a 7 días de la siembra prevista. Fecha mínima: {fecha_minima.isoformat()}."
        )
    if fecha_evento > lote.fecha_siembra:
        raise HTTPException(status_code=422, detail="La preparación Biofloc debe ocurrir antes o hasta la fecha prevista de siembra.")
    validar_evento_no_futuro(data.fecha_hora, "la aplicación de acondicionamiento Biofloc")

def listar_por_lote(db: Session, lote_id: int) -> list[AcondicionamientoBioflocEstanque]:
    return (
        db.query(AcondicionamientoBioflocEstanque)
        .filter(AcondicionamientoBioflocEstanque.lote_id == lote_id)
        .order_by(AcondicionamientoBioflocEstanque.fecha_hora.desc(), AcondicionamientoBioflocEstanque.id.desc())
        .all()
    )

def crear(db: Session, data: AcondicionamientoBioflocEstanqueCreate, usuario_id: int) -> AcondicionamientoBioflocEstanque:
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    if lote.estado.nombre != "PLANIFICADO":
        raise HTTPException(
            status_code=422,
            detail="El acondicionamiento previo a la siembra solo puede registrarse en un lote PLANIFICADO."
        )

    _validar_fecha(data, lote)

    tipo = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.id == data.tipo_aplicacion_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de aplicación Biofloc no encontrado")

    producto = None
    if data.producto_id is not None:
        producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
        if not producto or not producto.activo:
            raise HTTPException(status_code=422, detail="El producto seleccionado no existe o está inactivo")
        categoria = db.query(CategoriaInventario).filter(CategoriaInventario.id == producto.categoria_id).first()
        esperado = {
            "FUENTE_CARBONO": "FUENTE_CARBONO",
            "PROBIOTICO": "PROBIOTICO",
            "CORRECTIVO": "CORRECTIVO",
        }.get(_rol_tipo(tipo))
        if _rol_tipo(tipo) == "PURGA":
            raise HTTPException(status_code=422, detail="Una PURGA no debe consumir un producto de inventario")
        if esperado and (not categoria or categoria.nombre != esperado):
            raise HTTPException(status_code=422, detail=f"El producto no corresponde al tipo {tipo.nombre}")

    generar_salida = data.producto_id is not None and data.cantidad is not None and data.cantidad > 0
    salida_id = _obtener_tipo_salida_id(db) if generar_salida else None

    nuevo = AcondicionamientoBioflocEstanque(
        lote_id=lote.id,
        estanque_id=lote.estanque_id,
        tipo_aplicacion_id=data.tipo_aplicacion_id,
        producto_id=data.producto_id,
        fecha_hora=data.fecha_hora,
        fecha_siembra_prevista=lote.fecha_siembra,
        cantidad=data.cantidad,
        unidad=data.unidad,
        aireacion_activa=data.aireacion_activa,
        observaciones=data.observaciones,
        registrado_por=usuario_id,
    )
    db.add(nuevo)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")

    if generar_salida:
        mov = MovimientoInventarioCreate(
            producto_id=data.producto_id,  # type: ignore[arg-type]
            tipo_movimiento_id=salida_id,
            cantidad=Decimal(str(data.cantidad)),
            fecha_hora=data.fecha_hora,
            referencia_tipo="ACONDICIONAMIENTO_BIOFLOC",
            referencia_id=nuevo.id,
            observaciones=f"Acondicionamiento Biofloc - Lote {lote.codigo} - Estanque {lote.estanque.codigo}",
        )
        try:
            crear_movimiento_inventario(db, mov, usuario_id, flush_only=True)
        except HTTPException:
            db.rollback()
            raise

    db.add(Auditoria(
        usuario_id=usuario_id,
        tabla="acondicionamientos_biofloc_estanque",
        registro_id=nuevo.id,
        accion="INSERT",
        detalle={
            "lote_id": lote.id,
            "estanque_id": lote.estanque_id,
            "tipo_aplicacion_id": data.tipo_aplicacion_id,
            "producto_id": data.producto_id,
            "cantidad": float(data.cantidad) if data.cantidad is not None else None,
            "fecha_siembra_prevista": lote.fecha_siembra.isoformat(),
            "aireacion_activa": data.aireacion_activa,
            "inventario": generar_salida,
        },
    ))
    db.commit()
    db.refresh(nuevo)
    return nuevo
