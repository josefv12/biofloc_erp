from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.alarma_sistema import AlarmaCreate, AlarmaUpdate, AlarmaOut
from app.services.auth_service import get_current_user
from app.services import alarma_sistema_service as svc

router = APIRouter()
ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[AlarmaOut])
def listar(
    tipo_alarma_id: Optional[int] = None,
    nivel_alarma_id: Optional[int] = None,
    estado_alarma_id: Optional[int] = None,
    lote_id: Optional[int] = None,
    equipo_id: Optional[int] = None,
    evento_energia_id: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_alarmas(
        db,
        tipo_alarma_id=tipo_alarma_id,
        nivel_alarma_id=nivel_alarma_id,
        estado_alarma_id=estado_alarma_id,
        lote_id=lote_id,
        equipo_id=equipo_id,
        evento_energia_id=evento_energia_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get("/{alarma_id}", response_model=AlarmaOut)
def obtener(alarma_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_alarma(db, alarma_id)


@router.post("/", response_model=AlarmaOut, status_code=status.HTTP_201_CREATED)
def crear(data: AlarmaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_alarma(db, data, usuario_id=current_user.id)


@router.put("/{alarma_id}", response_model=AlarmaOut)
def actualizar(alarma_id: int, data: AlarmaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.actualizar_alarma(db, alarma_id, data, usuario_id=current_user.id)
