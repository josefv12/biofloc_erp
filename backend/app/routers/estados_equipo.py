from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.equipo import EstadoEquipoCreate, EstadoEquipoUpdate, EstadoEquipoOut
from app.services.auth_service import get_current_user
from app.services import catalogo_equipo_service as svc

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


@router.get("/", response_model=list[EstadoEquipoOut])
def listar(solo_activos: bool = False, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_estados_equipo(db, solo_activos=solo_activos)


@router.get("/{estado_id}", response_model=EstadoEquipoOut)
def obtener(estado_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_estado_equipo(db, estado_id)


@router.post("/", response_model=EstadoEquipoOut, status_code=status.HTTP_201_CREATED)
def crear(data: EstadoEquipoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_estado_equipo(db, data, usuario_id=current_user.id)


@router.put("/{estado_id}", response_model=EstadoEquipoOut)
def actualizar(estado_id: int, data: EstadoEquipoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_estado_equipo(db, estado_id, data, usuario_id=current_user.id)
