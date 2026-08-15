"""
Router /api/v1/tipos-movimiento-inventario
RBAC:
  GET : 3 roles
  POST/PUT : ADMINISTRADOR + TECNICO
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.tipo_movimiento_inventario import (
    TipoMovimientoInventarioCreate,
    TipoMovimientoInventarioUpdate,
    TipoMovimientoInventarioOut,
)
from app.services.auth_service import get_current_user
from app.services import tipo_movimiento_inventario_service as svc

router = APIRouter()

ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[TipoMovimientoInventarioOut])
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_tipos_movimiento_inventario(db)


@router.get("/{tipo_id}", response_model=TipoMovimientoInventarioOut)
def obtener(
    tipo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_tipo_movimiento_inventario(db, tipo_id)


@router.post("/", response_model=TipoMovimientoInventarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: TipoMovimientoInventarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_tipo_movimiento_inventario(db, data, usuario_id=current_user.id)


@router.put("/{tipo_id}", response_model=TipoMovimientoInventarioOut)
def actualizar(
    tipo_id: int,
    data: TipoMovimientoInventarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_tipo_movimiento_inventario(db, tipo_id, data, usuario_id=current_user.id)
