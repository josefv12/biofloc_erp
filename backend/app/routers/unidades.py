"""
Router /api/v1/unidades
RBAC:
  GET : 3 roles
  POST/PUT: ADMINISTRADOR + TECNICO
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.unidad import UnidadCreate, UnidadUpdate, UnidadOut
from app.services.auth_service import get_current_user
from app.services import unidad_service as svc

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


@router.get("/", response_model=list[UnidadOut])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_unidades(db, solo_activos=solo_activos)


@router.get("/{unidad_id}", response_model=UnidadOut)
def obtener(
    unidad_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_unidad(db, unidad_id)


@router.post("/", response_model=UnidadOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: UnidadCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_unidad(db, data, usuario_id=current_user.id)


@router.put("/{unidad_id}", response_model=UnidadOut)
def actualizar(
    unidad_id: int,
    data: UnidadUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_unidad(db, unidad_id, data, usuario_id=current_user.id)
