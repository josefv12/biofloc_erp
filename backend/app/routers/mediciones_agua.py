"""
Router para /api/v1/mediciones-agua

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET, POST

Decisión de diseño:
  La tabla mediciones_agua es inmutable y no cuenta con updated_at.
  Por lo tanto, no se exponen endpoints PUT/DELETE.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.medicion_agua import MedicionAguaCreate, MedicionAguaOut
from app.services.auth_service import get_current_user
from app.services import medicion_agua_service as svc

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
# GET /api/v1/mediciones-agua
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[MedicionAguaOut],
    summary="Listar mediciones de agua",
    description=(
        "Devuelve el listado de mediciones de agua registradas, ordenadas por fecha descendente. "
        "Se puede filtrar por lote_id y parametro_id. Acceso: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    parametro_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.listar_mediciones_agua(db, lote_id=lote_id, parametro_id=parametro_id)


# ---------------------------------------------------------------------------
# GET /api/v1/mediciones-agua/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{medicion_id}",
    response_model=MedicionAguaOut,
    summary="Obtener medición de agua por ID",
    description="Devuelve el detalle de una medición de agua específica por su ID. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    medicion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.obtener_medicion_agua(db, medicion_id)


# ---------------------------------------------------------------------------
# POST /api/v1/mediciones-agua
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=MedicionAguaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar medición de agua",
    description="Registra una nueva medición de parámetro de agua en un lote. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def crear(
    data: MedicionAguaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.crear_medicion_agua(db, data, usuario_id=current_user.id)
