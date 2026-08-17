from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.services.auth_service import get_current_user
from app.services import dashboard_service as svc
from app.schemas.dashboard import (
    DashboardResumenOut, DashboardInventarioOut, DashboardComprasOut,
    DashboardVentasOut, DashboardGastosOut, DashboardEquiposOut,
    DashboardEnergiaOut, DashboardAlarmasOut, DashboardProduccionOut,
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


def _auth(db: Session, current_user: Usuario):
    _require_roles(current_user, db, ROLES_LECTURA)


def _validar_periodo(fecha_desde: Optional[date], fecha_hasta: Optional[date]):
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=422, detail="fecha_desde debe ser <= fecha_hasta")


def _resumen_impl(fecha_desde, fecha_hasta, db, current_user):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.resumen(db, fecha_desde, fecha_hasta)


@router.get("/", response_model=DashboardResumenOut)
def dashboard_root(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return _resumen_impl(fecha_desde, fecha_hasta, db, current_user)


@router.get("/resumen", response_model=DashboardResumenOut)
def dashboard_resumen(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return _resumen_impl(fecha_desde, fecha_hasta, db, current_user)


@router.get("/inventario", response_model=DashboardInventarioOut)
def inventario(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.inventario(db, fecha_desde, fecha_hasta)


@router.get("/compras", response_model=DashboardComprasOut)
def compras(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.compras(db, fecha_desde, fecha_hasta)


@router.get("/ventas", response_model=DashboardVentasOut)
def ventas(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.ventas(db, fecha_desde, fecha_hasta)


@router.get("/gastos", response_model=DashboardGastosOut)
def gastos(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.gastos(db, fecha_desde, fecha_hasta)


@router.get("/equipos", response_model=DashboardEquiposOut)
def equipos(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.equipos(db, fecha_desde, fecha_hasta)


@router.get("/energia", response_model=DashboardEnergiaOut)
def energia(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.energia(db, fecha_desde, fecha_hasta)


@router.get("/alarmas", response_model=DashboardAlarmasOut)
def alarmas(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.alarmas(db, fecha_desde, fecha_hasta)


@router.get("/produccion", response_model=DashboardProduccionOut)
def produccion(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _auth(db, current_user)
    _validar_periodo(fecha_desde, fecha_hasta)
    return svc.produccion(db, fecha_desde, fecha_hasta)
