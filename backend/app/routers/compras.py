"""
Router /api/v1/compras
Registro maestro + detalle inmutable. POST 1-shot / GET lista / GET detalle.
Sin PUT / PATCH / DELETE.

RBAC:
  GET / y /{id} : ADMINISTRADOR, TECNICO, OPERARIO
  POST          : ADMINISTRADOR, TECNICO, OPERARIO
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.compra import CompraCreate, CompraOut, CompraDetalleOut
from app.services.auth_service import get_current_user
from app.services import compra_service as svc

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


@router.get("/", response_model=list[CompraOut])
def listar(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    proveedor: Optional[str] = None,
    producto_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_compras(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        proveedor=proveedor,
        producto_id=producto_id,
        registrado_por=registrado_por,
    )


@router.get("/{compra_id}", response_model=CompraDetalleOut)
def obtener(
    compra_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    c = svc.obtener_compra(db, compra_id)
    movs = svc.obtener_movimientos_asociados(db, compra_id)
    return CompraDetalleOut(
        id=c.id,
        fecha=c.fecha,
        proveedor=c.proveedor,
        total=c.total,
        observaciones=c.observaciones,
        registrado_por=c.registrado_por,
        created_at=c.created_at,
        detalles=list(c.detalles),
        movimientos=movs,
    )


@router.post("/", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: CompraCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_compra(db, data, usuario_id=current_user.id)
