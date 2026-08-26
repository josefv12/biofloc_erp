"""Router GET /api/v1/estados-estanque

Catálogo de estados de estanque. Solo consulta.

RBAC: GET ADMINISTRADOR, TECNICO, OPERARIO.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.estanque import EstadoEstanqueOut
from app.services import catalogo_produccion_service as svc
from app.services.auth_service import get_current_user

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[EstadoEstanqueOut])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_estados_estanque(db, solo_activos=solo_activos)
