from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.mantenimiento import MantenimientoCreate, MantenimientoOut
from app.services.auth_service import get_current_user
from app.services import mantenimiento_service as svc

router = APIRouter()
ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[MantenimientoOut])
def listar(
    equipo_id: Optional[int] = None,
    tipo_mantenimiento_id: Optional[int] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_mantenimientos(
        db, equipo_id=equipo_id, tipo_mantenimiento_id=tipo_mantenimiento_id,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, registrado_por=registrado_por,
    )


@router.get("/{mant_id}", response_model=MantenimientoOut)
def obtener(mant_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_mantenimiento(db, mant_id)


@router.post("/", response_model=MantenimientoOut, status_code=status.HTTP_201_CREATED)
def crear(data: MantenimientoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_mantenimiento(db, data, usuario_id=current_user.id)
