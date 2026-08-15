"""
Router para /api/v1/biometrias

Roles y permisos:
- ADMINISTRADOR : GET, POST
- TECNICO       : GET, POST
- OPERARIO      : GET (solo consulta)

Decisión de diseño:
  La tabla biometrias no tiene columna updated_at ni UPDATE en el schema,
  por lo que NO se expone endpoint PUT.
  Los registros de biometría son inmutables por diseño.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.biometria import BiometriaCreate, BiometriaOut
from app.services.auth_service import get_current_user
from app.services import biometria_service as svc

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
# GET /api/v1/biometrias
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[BiometriaOut],
    summary="Listar biometrías",
    description=(
        "Devuelve el listado de biometrías registradas, ordenadas por fecha descendente. "
        "Se puede filtrar por lote_id. Acceso: todos los roles autenticados."
    ),
)
def listar(
    lote_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return svc.listar_biometrias(db, lote_id=lote_id)


# ---------------------------------------------------------------------------
# GET /api/v1/biometrias/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/{biometria_id}",
    response_model=BiometriaOut,
    summary="Obtener biometría por ID",
    description="Devuelve una biometría específica. Acceso: todos los roles autenticados.",
)
def obtener(
    biometria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return svc.obtener_biometria(db, biometria_id)


# ---------------------------------------------------------------------------
# POST /api/v1/biometrias
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=BiometriaOut,
    status_code=201,
    summary="Registrar biometría",
    description=(
        "Registra un nuevo muestreo biométrico para un lote. "
        "Valida que el lote exista y que la fecha no sea anterior a la siembra. "
        "Roles permitidos: ADMINISTRADOR, TECNICO."
    ),
)
def crear(
    data: BiometriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO"})
    return svc.crear_biometria(db, data, current_user.id)
