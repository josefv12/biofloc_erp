"""
Router para /api/v1/estanques

Roles y permisos:
- ADMINISTRADOR : GET, POST, PUT
- TECNICO       : GET, PUT (estado/operacional)
- OPERARIO      : GET (solo consulta)

Decisión de diseño: No se expone DELETE físico.
Para desactivar un estanque se usa PUT con activo=False.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.estanque import EstanqueCreate, EstanqueUpdate, EstanqueOut
from app.services.auth_service import get_current_user
from app.services import estanque_service as svc

router = APIRouter()

ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}
ROLES_SOLO_LECTURA = {"OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación")


@router.get("/", response_model=list[EstanqueOut], summary="Listar estanques")
def listar(
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return svc.listar_estanques(db, solo_activos)


@router.get("/{estanque_id}", response_model=EstanqueOut, summary="Obtener estanque")
def obtener(
    estanque_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return svc.obtener_estanque(db, estanque_id)


@router.post("/", response_model=EstanqueOut, status_code=201, summary="Crear estanque")
def crear(
    data: EstanqueCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR"})
    return svc.crear_estanque(db, data, current_user.id)


@router.put("/{estanque_id}", response_model=EstanqueOut, summary="Actualizar estanque")
def actualizar(
    estanque_id: int,
    data: EstanqueUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_estanque(db, estanque_id, data, current_user.id)
