from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.venta import VentaCreate, VentaOut
from app.services.auth_service import get_current_user
from app.services import venta_service as svc

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


@router.get("/", response_model=list[VentaOut])
def listar(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    cliente: Optional[str] = None,
    lote_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_ventas(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        lote_id=lote_id,
        registrado_por=registrado_por,
    )


@router.get("/{venta_id}", response_model=VentaOut)
def obtener(
    venta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_venta(db, venta_id)


@router.post("/", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_venta(db, data, usuario_id=current_user.id)
