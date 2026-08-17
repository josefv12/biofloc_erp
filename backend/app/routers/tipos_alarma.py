from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.alarma_sistema import TipoAlarmaCreate, TipoAlarmaUpdate, TipoAlarmaOut
from app.services.auth_service import get_current_user
from app.services import catalogo_alarma_service as svc

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[TipoAlarmaOut])
def listar(solo_activos: bool = False, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_tipos_alarma(db, solo_activos=solo_activos)


@router.get("/{tipo_id}", response_model=TipoAlarmaOut)
def obtener(tipo_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_tipo_alarma(db, tipo_id)


@router.post("/", response_model=TipoAlarmaOut, status_code=status.HTTP_201_CREATED)
def crear(data: TipoAlarmaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_tipo_alarma(db, data, usuario_id=current_user.id)


@router.put("/{tipo_id}", response_model=TipoAlarmaOut)
def actualizar(tipo_id: int, data: TipoAlarmaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_tipo_alarma(db, tipo_id, data, usuario_id=current_user.id)
