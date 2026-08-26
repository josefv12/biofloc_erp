"""Router /api/v1/especies

Catálogo maestro de producción.

RBAC:
- GET  ADMINISTRADOR, TECNICO, OPERARIO
- POST/PUT ADMINISTRADOR
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.catalogo_produccion import EspecieCatalogoOut, EspecieCreate, EspecieUpdate
from app.services import especie_service as svc
from app.services.auth_service import get_current_user

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[EspecieCatalogoOut])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_especies(db, solo_activos=solo_activos)


@router.get("/{especie_id}", response_model=EspecieCatalogoOut)
def obtener(
    especie_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_especie(db, especie_id)


@router.post("/", response_model=EspecieCatalogoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: EspecieCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_especie(db, data, usuario_id=current_user.id)


@router.put("/{especie_id}", response_model=EspecieCatalogoOut)
def actualizar(
    especie_id: int,
    data: EspecieUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_especie(db, especie_id, data, usuario_id=current_user.id)
