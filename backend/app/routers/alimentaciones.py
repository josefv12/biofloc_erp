"""
Router para /api/v1/alimentaciones

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET, POST

Decisión de diseño:
  La tabla alimentaciones es inmutable y no cuenta con updated_at.
  Por lo tanto, no se exponen endpoints PUT/DELETE.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.alimentacion import AlimentacionCreate, AlimentacionOut
from app.services.auth_service import get_current_user
from app.services import alimentacion_service as svc

router = APIRouter()


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


# ---------------------------------------------------------------------------
# GET /api/v1/alimentaciones
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[AlimentacionOut],
    summary="Listar alimentaciones",
    description=(
        "Devuelve el listado de alimentaciones registradas, ordenadas por fecha descendente. "
        "Se puede filtrar por lote_id. Acceso: todos los roles autenticados."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.listar_alimentaciones(db, lote_id=lote_id)


# ---------------------------------------------------------------------------
# GET /api/v1/alimentaciones/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{alimentacion_id}",
    response_model=AlimentacionOut,
    summary="Obtener alimentación por ID",
    description="Devuelve un registro de alimentación específico. Acceso: todos los roles autenticados.",
)
def obtener(
    alimentacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.obtener_alimentacion(db, alimentacion_id)


# ---------------------------------------------------------------------------
# POST /api/v1/alimentaciones
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=AlimentacionOut,
    status_code=201,
    summary="Registrar alimentación",
    description=(
        "Registra un evento de alimentación para un lote. "
        "Valida que el lote y el producto existan, y que la fecha sea válida. "
        "Roles permitidos: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def crear(
    data: AlimentacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.crear_alimentacion(db, data, current_user.id)
