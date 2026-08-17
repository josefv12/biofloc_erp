from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.equipo import EquipoCreate, EquipoUpdate, EquipoOut
from app.services.auth_service import get_current_user
from app.services import equipo_service as svc

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[EquipoOut])
def listar(
    solo_activos: bool = False,
    tipo_equipo_id: Optional[int] = None,
    estado_id: Optional[int] = None,
    codigo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_equipos(
        db, solo_activos=solo_activos, tipo_equipo_id=tipo_equipo_id,
        estado_id=estado_id, codigo=codigo,
    )


@router.get("/{equipo_id}", response_model=EquipoOut)
def obtener(equipo_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_equipo(db, equipo_id)


@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear(data: EquipoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_equipo(db, data, usuario_id=current_user.id)


@router.put("/{equipo_id}", response_model=EquipoOut)
def actualizar(equipo_id: int, data: EquipoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_equipo(db, equipo_id, data, usuario_id=current_user.id)
