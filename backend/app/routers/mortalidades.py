"""
Router para /api/v1/mortalidades

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET, POST

Decisión de diseño:
  La tabla mortalidades es inmutable y no cuenta con updated_at.
  Por lo tanto, no se exponen endpoints PUT/DELETE.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.mortalidad import MortalidadCreate, MortalidadOut
from app.services.auth_service import get_current_user
from app.services import mortalidad_service as svc

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
# GET /api/v1/mortalidades
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[MortalidadOut],
    summary="Listar mortalidades",
    description=(
        "Devuelve el listado de mortalidades registradas, ordenadas por fecha descendente. "
        "Se puede filtrar por lote_id. Acceso: todos los roles autenticados."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.listar_mortalidades(db, lote_id=lote_id)


# ---------------------------------------------------------------------------
# GET /api/v1/mortalidades/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{mortalidad_id}",
    response_model=MortalidadOut,
    summary="Obtener mortalidad por ID",
    description="Devuelve una mortalidad específica. Acceso: todos los roles autenticados.",
)
def obtener(
    mortalidad_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.obtener_mortalidad(db, mortalidad_id)


# ---------------------------------------------------------------------------
# POST /api/v1/mortalidades
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=MortalidadOut,
    status_code=201,
    summary="Registrar mortalidad",
    description=(
        "Registra un evento de mortalidad para un lote. "
        "Valida que el lote exista, que la fecha sea válida, y que la mortalidad "
        "acumulada no exceda la cantidad sembrada. "
        "Roles permitidos: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def crear(
    data: MortalidadCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.crear_mortalidad(db, data, current_user.id)
