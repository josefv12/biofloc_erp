"""
Router para /api/v1/parametros-agua

Roles y permisos:
- ADMINISTRADOR : GET, POST, PUT
- TECNICO       : GET, POST, PUT
- OPERARIO      : GET
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.parametro_agua import ParametroAguaCreate, ParametroAguaUpdate, ParametroAguaOut
from app.services.auth_service import get_current_user
from app.services import parametro_agua_service as svc

router = APIRouter()

ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


# ---------------------------------------------------------------------------
# GET /api/v1/parametros-agua
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[ParametroAguaOut],
    summary="Listar parámetros de agua",
    description="Devuelve el catálogo de parámetros de calidad de agua. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_parametros_agua(db, solo_activos=solo_activos)


# ---------------------------------------------------------------------------
# GET /api/v1/parametros-agua/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{parametro_id}",
    response_model=ParametroAguaOut,
    summary="Obtener parámetro de agua por ID",
    description="Devuelve el detalle de un parámetro de agua por su ID. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    parametro_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_parametro_agua(db, parametro_id)


# ---------------------------------------------------------------------------
# POST /api/v1/parametros-agua
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=ParametroAguaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar parámetro de agua",
    description="Crea un nuevo parámetro de calidad de agua. Acceso: ADMINISTRADOR, TECNICO.",
)
def crear(
    data: ParametroAguaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_parametro_agua(db, data, usuario_id=current_user.id)


# ---------------------------------------------------------------------------
# PUT /api/v1/parametros-agua/{id}
# ---------------------------------------------------------------------------
@router.put(
    "/{parametro_id}",
    response_model=ParametroAguaOut,
    summary="Actualizar parámetro de agua",
    description="Actualiza un parámetro de calidad de agua existente. Acceso: ADMINISTRADOR, TECNICO.",
)
def actualizar(
    parametro_id: int,
    data: ParametroAguaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_parametro_agua(db, parametro_id, data, usuario_id=current_user.id)
