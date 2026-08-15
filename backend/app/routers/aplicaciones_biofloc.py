"""
Router para /api/v1/aplicaciones-biofloc

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET, POST

Decisión de diseño:
  aplicaciones_biofloc son registros históricos → no se exponen PUT/DELETE.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.aplicacion_biofloc import AplicacionBioflocCreate, AplicacionBioflocOut
from app.services.auth_service import get_current_user
from app.services import aplicacion_biofloc_service as svc

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
# GET /api/v1/aplicaciones-biofloc
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[AplicacionBioflocOut],
    summary="Listar aplicaciones Biofloc",
    description=(
        "Devuelve el listado de aplicaciones/tratamientos Biofloc registradas, "
        "ordenadas por fecha descendente. Se puede filtrar por lote_id. "
        "Acceso: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.listar_aplicaciones_biofloc(db, lote_id=lote_id)


# ---------------------------------------------------------------------------
# GET /api/v1/aplicaciones-biofloc/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{aplicacion_id}",
    response_model=AplicacionBioflocOut,
    summary="Obtener aplicación Biofloc por ID",
    description="Devuelve el detalle de una aplicación Biofloc por su ID. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    aplicacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.obtener_aplicacion_biofloc(db, aplicacion_id)


# ---------------------------------------------------------------------------
# POST /api/v1/aplicaciones-biofloc
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=AplicacionBioflocOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar aplicación Biofloc",
    description="Registra una nueva aplicación/tratamiento Biofloc en un lote. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def crear(
    data: AplicacionBioflocCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.crear_aplicacion_biofloc(db, data, usuario_id=current_user.id)
