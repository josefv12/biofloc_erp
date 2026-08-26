"""
Router para /api/v1/referencias-agua

Roles y permisos (catálogo maestro de producción):
- ADMINISTRADOR : GET, POST, PUT
- TECNICO       : GET
- OPERARIO      : GET
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.referencia_agua import ReferenciaAguaCreate, ReferenciaAguaUpdate, ReferenciaAguaOut
from app.services.auth_service import get_current_user
from app.services import referencia_agua_service as svc

router = APIRouter()

ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


# ---------------------------------------------------------------------------
# GET /api/v1/referencias-agua
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[ReferenciaAguaOut],
    summary="Listar referencias de agua",
    description=(
        "Devuelve la lista de rangos y valores de referencia de agua por especie, etapa y parámetro. "
        "Acceso: ADMINISTRADOR, TECNICO, OPERARIO."
    ),
)
def listar(
    especie_id: Optional[int] = None,
    etapa_productiva_id: Optional[int] = None,
    parametro_id: Optional[int] = None,
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_referencias_agua(
        db,
        especie_id=especie_id,
        etapa_productiva_id=etapa_productiva_id,
        parametro_id=parametro_id,
        solo_activos=solo_activos
    )


# ---------------------------------------------------------------------------
# GET /api/v1/referencias-agua/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{referencia_id}",
    response_model=ReferenciaAguaOut,
    summary="Obtener referencia de agua por ID",
    description="Devuelve el detalle de una referencia de agua específica. Acceso: ADMINISTRADOR, TECNICO, OPERARIO.",
)
def obtener(
    referencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_referencia_agua(db, referencia_id)


# ---------------------------------------------------------------------------
# POST /api/v1/referencias-agua
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=ReferenciaAguaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar referencia de agua",
    description="Crea un nuevo rango/referencia de parámetro de agua. Acceso: ADMINISTRADOR.",
)
def crear(
    data: ReferenciaAguaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_referencia_agua(db, data, usuario_id=current_user.id)


# ---------------------------------------------------------------------------
# PUT /api/v1/referencias-agua/{id}
# ---------------------------------------------------------------------------
@router.put(
    "/{referencia_id}",
    response_model=ReferenciaAguaOut,
    summary="Actualizar referencia de agua",
    description="Actualiza los valores o el estado de una referencia de agua existente. Acceso: ADMINISTRADOR.",
)
def actualizar(
    referencia_id: int,
    data: ReferenciaAguaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_referencia_agua(db, referencia_id, data, usuario_id=current_user.id)
