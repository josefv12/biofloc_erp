from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.falla import FallaCreate, FallaUpdate, FallaOut
from app.services.auth_service import get_current_user
from app.services import falla_service as svc

router = APIRouter()
ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[FallaOut])
def listar(
    equipo_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    registrada_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_fallas(
        db, equipo_id=equipo_id, fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta, registrada_por=registrada_por,
    )


@router.get("/{falla_id}", response_model=FallaOut)
def obtener(falla_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_falla(db, falla_id)


@router.post("/", response_model=FallaOut, status_code=status.HTTP_201_CREATED)
def crear(data: FallaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_falla(db, data, usuario_id=current_user.id)


@router.put("/{falla_id}", response_model=FallaOut)
def actualizar(falla_id: int, data: FallaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.actualizar_falla(db, falla_id, data, usuario_id=current_user.id)
