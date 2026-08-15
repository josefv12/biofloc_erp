"""
Router /api/v1/movimientos-inventario
Histórico INMUTABLE: solo GET (lista + detalle) y POST.
Sin PUT, sin DELETE.

RBAC:
  GET / y /{id}  : 3 roles (ADMINISTRADOR, TECNICO, OPERARIO)
  POST           : 3 roles
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.movimiento_inventario import MovimientoInventarioCreate, MovimientoInventarioOut
from app.services.auth_service import get_current_user
from app.services import movimiento_inventario_service as svc

router = APIRouter()

ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[MovimientoInventarioOut])
def listar(
    producto_id: Optional[int] = None,
    tipo_movimiento_id: Optional[int] = None,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_movimientos_inventario(
        db,
        producto_id=producto_id,
        tipo_movimiento_id=tipo_movimiento_id,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get("/{movimiento_id}", response_model=MovimientoInventarioOut)
def obtener(
    movimiento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_movimiento_inventario(db, movimiento_id)


@router.post("/", response_model=MovimientoInventarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: MovimientoInventarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_movimiento_inventario(db, data, usuario_id=current_user.id)
