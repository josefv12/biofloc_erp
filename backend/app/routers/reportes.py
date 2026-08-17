from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.services.auth_service import get_current_user
from app.services import reportes_service as svc
from app.schemas.reportes import (
    ReporteVentasOut, ReporteComprasOut, ReporteGastosOut,
    ReporteInventarioOut, ReporteMovimientosOut, ReporteComprasInventarioOut,
    ReporteProduccionOut, ReporteAguaOut, ReporteBioflocOut, ReporteAlimentacionOut,
    ReporteEquiposOut, ReporteMantenimientosOut, ReporteFallasOut,
    ReporteEnergiaOut, ReporteAlarmasOut,
)

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


def _guard(db: Session, current_user: Usuario, fecha_desde, fecha_hasta):
    _require_roles(current_user, db, ROLES_LECTURA)
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=422, detail="fecha_desde debe ser <= fecha_hasta")


@router.get("/ventas", response_model=ReporteVentasOut)
def reporte_ventas(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    cliente: Optional[str] = None, lote_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.ventas(db, fecha_desde, fecha_hasta, cliente, lote_id, registrado_por)


@router.get("/compras", response_model=ReporteComprasOut)
def reporte_compras(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    proveedor: Optional[str] = None, producto_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.compras(db, fecha_desde, fecha_hasta, proveedor, producto_id, registrado_por)


@router.get("/gastos", response_model=ReporteGastosOut)
def reporte_gastos(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    categoria_id: Optional[int] = None, lote_id: Optional[int] = None,
    proveedor: Optional[str] = None, registrado_por: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.gastos(db, fecha_desde, fecha_hasta, categoria_id, lote_id, proveedor, registrado_por)


@router.get("/inventario", response_model=ReporteInventarioOut)
def reporte_inventario(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    clasificacion: Optional[str] = None, solo_activos: bool = True,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.inventario(db, fecha_desde, fecha_hasta, clasificacion, solo_activos)


@router.get("/inventario/movimientos", response_model=ReporteMovimientosOut)
def reporte_movimientos(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    producto_id: Optional[int] = None, referencia_tipo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.movimientos(db, fecha_desde, fecha_hasta, producto_id, referencia_tipo)


@router.get("/compras-inventario", response_model=ReporteComprasInventarioOut)
def reporte_compras_inventario(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.compras_inventario(db, fecha_desde, fecha_hasta)


@router.get("/produccion", response_model=ReporteProduccionOut)
def reporte_produccion(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.produccion(db, fecha_desde, fecha_hasta, lote_id)


@router.get("/agua", response_model=ReporteAguaOut)
def reporte_agua(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    lote_id: Optional[int] = None, parametro_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.agua(db, fecha_desde, fecha_hasta, lote_id, parametro_id)


@router.get("/biofloc", response_model=ReporteBioflocOut)
def reporte_biofloc(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.biofloc(db, fecha_desde, fecha_hasta, lote_id)


@router.get("/alimentacion", response_model=ReporteAlimentacionOut)
def reporte_alimentacion(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.alimentacion(db, fecha_desde, fecha_hasta, lote_id)


@router.get("/equipos", response_model=ReporteEquiposOut)
def reporte_equipos(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.equipos(db, fecha_desde, fecha_hasta, activo)


@router.get("/mantenimientos", response_model=ReporteMantenimientosOut)
def reporte_mantenimientos(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    equipo_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.mantenimientos(db, fecha_desde, fecha_hasta, equipo_id)


@router.get("/fallas", response_model=ReporteFallasOut)
def reporte_fallas(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    equipo_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.fallas(db, fecha_desde, fecha_hasta, equipo_id)


@router.get("/energia", response_model=ReporteEnergiaOut)
def reporte_energia(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.energia(db, fecha_desde, fecha_hasta, tipo)


@router.get("/alarmas", response_model=ReporteAlarmasOut)
def reporte_alarmas(
    fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
    estado_alarma_id: Optional[int] = None, tipo_alarma_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user),
):
    _guard(db, current_user, fecha_desde, fecha_hasta)
    return svc.alarmas(db, fecha_desde, fecha_hasta, estado_alarma_id, tipo_alarma_id)
