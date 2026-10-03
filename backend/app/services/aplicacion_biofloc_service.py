"""
Servicio para operaciones CRUD de aplicaciones_biofloc.

Reglas aplicadas:
- lote_id debe existir.
- tipo_aplicacion_id debe existir.
- fecha_hora no puede ser anterior a fecha_siembra del lote.
- cantidad: NULL permitido; si se envía debe ser >= 0.
- producto_id: si se envía junto con cantidad > 0, se genera automáticamente
  un movimiento de SALIDA de inventario (transaccional).
- No se expone UPDATE ni DELETE (registros históricos).
- Auditoría INSERT por cada creación exitosa.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.aplicacion_biofloc import AplicacionBiofloc
from app.models.lote import Lote
from app.models.producto import Producto
from app.models.categoria_inventario import CategoriaInventario
from app.models.tipo_aplicacion_biofloc import TipoAplicacionBiofloc
from app.models.auditoria import Auditoria
from app.schemas.aplicacion_biofloc import AplicacionBioflocCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.movimiento_inventario_service import crear_movimiento_inventario, _obtener_tipo_salida_id
from app.services.poblacion_lote import exigir_lote_en_produccion
from app.services.validaciones_temporales import validar_evento_lote


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="aplicaciones_biofloc",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_aplicaciones_biofloc(
    db: Session,
    lote_id: int | None = None
) -> list[AplicacionBiofloc]:
    q = db.query(AplicacionBiofloc)
    if lote_id:
        q = q.filter(AplicacionBiofloc.lote_id == lote_id)
    return q.order_by(AplicacionBiofloc.fecha_hora.desc()).all()


def obtener_aplicacion_biofloc(db: Session, aplicacion_id: int) -> AplicacionBiofloc:
    a = db.query(AplicacionBiofloc).filter(AplicacionBiofloc.id == aplicacion_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Aplicación Biofloc no encontrada")
    return a


def _validar_producto_para_cantidad(cantidad: Decimal | None, producto_id: int | None) -> None:
    if cantidad is not None and cantidad > 0 and producto_id is None:
        raise HTTPException(
            status_code=422,
            detail="Debe seleccionar un producto cuando la cantidad de la aplicación Biofloc es mayor que 0",
        )


def crear_aplicacion_biofloc(db: Session, data: AplicacionBioflocCreate, usuario_id: int) -> AplicacionBiofloc:
    # 1. Validar lote
    lote = db.query(Lote).filter(Lote.id == data.lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote id={data.lote_id} no existe")
    exigir_lote_en_produccion(db, lote)

    # 2. Validar tipo_aplicacion_id
    tipo = db.query(TipoAplicacionBiofloc).filter(TipoAplicacionBiofloc.id == data.tipo_aplicacion_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail=f"Tipo de aplicación Biofloc id={data.tipo_aplicacion_id} no existe")

    validar_evento_lote(data.fecha_hora, lote.fecha_siembra, "la aplicación Biofloc")

    # 4. Validar cantidad >= 0 si se proporciona
    if data.cantidad is not None and data.cantidad < 0:
        raise HTTPException(status_code=422, detail="La cantidad debe ser mayor o igual a 0")

    # Validar que el producto corresponda al tipo de aplicación seleccionado.
    if data.producto_id is not None:
        producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto id={data.producto_id} no existe")
        if not producto.activo:
            raise HTTPException(status_code=422, detail="El producto seleccionado está inactivo")
        categoria = db.query(CategoriaInventario).filter(CategoriaInventario.id == producto.categoria_id).first()
        if not categoria:
            raise HTTPException(status_code=422, detail="El producto seleccionado no tiene una categoría válida")
        tipo_nombre = tipo.nombre.strip().upper()
        categoria_esperada = {
            "FUENTE_CARBONO": "FUENTE_CARBONO",
            "PROBIOTICO": "PROBIOTICO",
            "CORRECTIVO": "CORRECTIVO",
        }.get(tipo_nombre)
        if categoria_esperada is None:
            if tipo_nombre == "PURGA":
                raise HTTPException(status_code=422, detail="Una PURGA no debe registrar producto ni consumo de inventario")
        elif categoria.nombre != categoria_esperada:
            raise HTTPException(status_code=422, detail=f"El producto no corresponde al tipo de aplicación {tipo.nombre}")

    # Determinar si debe generar movimiento de inventario
    generar_movimiento = (
        data.producto_id is not None
        and data.cantidad is not None
        and data.cantidad > 0
    )

    tipo_salida_id = _obtener_tipo_salida_id(db) if generar_movimiento else None

    nuevo = AplicacionBiofloc(**data.model_dump(), registrado_por=usuario_id)
    db.add(nuevo)

    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {str(e)}")

    # Crear movimiento de SALIDA si aplica
    if generar_movimiento and tipo_salida_id is not None:
        mov_data = MovimientoInventarioCreate(
            producto_id=data.producto_id,  # type: ignore[arg-type]
            tipo_movimiento_id=tipo_salida_id,
            cantidad=Decimal(str(data.cantidad)),
            fecha_hora=data.fecha_hora,
            referencia_tipo="APLICACION_BIOFLOC",
            referencia_id=nuevo.id,
            observaciones=f"Consumo automático Biofloc - Lote {lote.codigo}",
        )
        try:
            crear_movimiento_inventario(db, mov_data, usuario_id, flush_only=True)
        except HTTPException:
            db.rollback()
            raise

    # Serializar Decimal para JSONB
    detalle = {
        "lote_id": data.lote_id,
        "tipo_aplicacion_id": data.tipo_aplicacion_id,
        "producto_id": data.producto_id,
        "cantidad": float(data.cantidad) if isinstance(data.cantidad, Decimal) else data.cantidad,
        "inventario": generar_movimiento,
    }

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, detalle)
    db.commit()
    db.refresh(nuevo)
    return nuevo
