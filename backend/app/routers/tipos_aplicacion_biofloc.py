"""
Router para /api/v1/tipos-aplicacion-biofloc

Roles y permisos:
- ADMINISTRADOR : GET, POST, PUT
- TECNICO       : GET, POST, PUT
- OPERARIO      : GET
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.tipo_aplicacion_biofloc import (
    TipoAplicacionBioflocCreate,
    TipoAplicacionBioflocUpdate,
    TipoAplicacionBioflocOut,
)
from app.services.auth_service import get_current_user
from app.services import tipo_aplicacion_biofloc_service as svc

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
# GET /api/v1/tipos-aplicacion-biofloc
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[TipoAplicacionBioflocOut],
    summary="Listar tipos de aplicación Biofloc",
    description="Devuelve el catálogo de tipos de tratamientos/aplicaciones Biofloc. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_tipos_aplicacion_biofloc(db, solo_activos=solo_activos)


# ---------------------------------------------------------------------------
# GET /api/v1/tipos-aplicacion-biofloc/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{tipo_id}",
    response_model=TipoAplicacionBioflocOut,
    summary="Obtener tipo de aplicación Biofloc por ID",
    description="Devuelve el detalle de un tipo de aplicación Biofloc por su ID. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    tipo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_tipo_aplicacion_biofloc(db, tipo_id)


# ---------------------------------------------------------------------------
# POST /api/v1/tipos-aplicacion-biofloc
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=TipoAplicacionBioflocOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar tipo de aplicación Biofloc",
    description="Crea un nuevo tipo de tratamiento o aplicación Biofloc. Acceso: ADMINISTRADOR, TECNICO.",
)
def crear(
    data: TipoAplicacionBioflocCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_tipo_aplicacion_biofloc(db, data, usuario_id=current_user.id)


# ---------------------------------------------------------------------------
# PUT /api/v1/tipos-aplicacion-biofloc/{id}
# ---------------------------------------------------------------------------
@router.put(
    "/{tipo_id}",
    response_model=TipoAplicacionBioflocOut,
    summary="Actualizar tipo de aplicación Biofloc",
    description="Actualiza un tipo de aplicación Biofloc existente. Acceso: ADMINISTRADOR, TECNICO.",
)
def actualizar(
    tipo_id: int,
    data: TipoAplicacionBioflocUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_tipo_aplicacion_biofloc(db, tipo_id, data, usuario_id=current_user.id)
