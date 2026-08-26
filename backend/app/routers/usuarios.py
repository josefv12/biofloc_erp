"""Router /api/v1/usuarios y /api/v1/roles

Solo ADMINISTRADOR. TECNICO y OPERARIO reciben 403.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.usuario import RolOut, UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuario_service as svc
from app.services.auth_service import get_current_user

router = APIRouter()
roles_router = APIRouter()
ROLES_ADMIN = {"ADMINISTRADOR"}


def _require_admin(usuario: Usuario, db: Session):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[UsuarioOut])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_admin(current_user, db)
    return svc.listar_usuarios(db, solo_activos=solo_activos)


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_admin(current_user, db)
    return svc.obtener_usuario(db, usuario_id)


@router.post("/", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_admin(current_user, db)
    return svc.crear_usuario(db, data, actor_id=current_user.id)


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_admin(current_user, db)
    return svc.actualizar_usuario(db, usuario_id, data, actor_id=current_user.id)


@roles_router.get("/", response_model=list[RolOut])
def listar_roles(
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_admin(current_user, db)
    return svc.listar_roles(db, solo_activos=solo_activos)
