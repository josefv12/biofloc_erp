from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.evento_energia import EventoEnergiaCreate, EventoEnergiaUpdate, EventoEnergiaOut
from app.services.auth_service import get_current_user
from app.services import evento_energia_service as svc

router = APIRouter()
ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[EventoEnergiaOut])
def listar(
    tipo: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    respaldo_activado: Optional[bool] = None,
    equipo_respaldo_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_eventos_energia(
        db, tipo=tipo, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        respaldo_activado=respaldo_activado, equipo_respaldo_id=equipo_respaldo_id,
        registrado_por=registrado_por,
    )


@router.get("/{evento_id}", response_model=EventoEnergiaOut)
def obtener(evento_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_evento_energia(db, evento_id)


@router.post("/", response_model=EventoEnergiaOut, status_code=status.HTTP_201_CREATED)
def crear(data: EventoEnergiaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_evento_energia(db, data, usuario_id=current_user.id)


@router.put("/{evento_id}", response_model=EventoEnergiaOut)
def actualizar(evento_id: int, data: EventoEnergiaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.actualizar_evento_energia(db, evento_id, data, usuario_id=current_user.id)
