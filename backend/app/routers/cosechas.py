"""
Router para /api/v1/cosechas

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET, POST

Decisión de diseño:
  La tabla cosechas es inmutable y no cuenta con updated_at.
  Por lo tanto, no se exponen endpoints PUT/DELETE.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.cosecha import CosechaCreate, CosechaOut
from app.services.auth_service import get_current_user
from app.services import cosecha_service as svc

router = APIRouter()

ROLES_PERMITIDOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


# ---------------------------------------------------------------------------
# GET /api/v1/cosechas
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[CosechaOut],
    summary="Listar cosechas",
    description=(
        "Devuelve el listado de cosechas registradas, ordenadas por fecha descendente. "
        "Se puede filtrar por lote_id. Acceso: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.listar_cosechas(db, lote_id=lote_id)


# ---------------------------------------------------------------------------
# GET /api/v1/cosechas/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{cosecha_id}",
    response_model=CosechaOut,
    summary="Obtener cosecha por ID",
    description="Devuelve el detalle de una cosecha específica por su ID. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    cosecha_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.obtener_cosecha(db, cosecha_id)


# ---------------------------------------------------------------------------
# POST /api/v1/cosechas
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=CosechaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cosecha",
    description="Registra una nueva cosecha asociada a un lote. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def crear(
    data: CosechaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.crear_cosecha(db, data, usuario_id=current_user.id)
