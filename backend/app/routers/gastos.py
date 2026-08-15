from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.gasto import GastoCreate, GastoOut
from app.services.auth_service import get_current_user
from app.services import gasto_service as svc

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


@router.get("/", response_model=list[GastoOut])
def listar(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    categoria_id: Optional[int] = None,
    lote_id: Optional[int] = None,
    proveedor: Optional[str] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_gastos(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        categoria_id=categoria_id,
        lote_id=lote_id,
        proveedor=proveedor,
        registrado_por=registrado_por,
    )


@router.get("/{gasto_id}", response_model=GastoOut)
def obtener(
    gasto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_gasto(db, gasto_id)


@router.post("/", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: GastoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_gasto(db, data, usuario_id=current_user.id)
