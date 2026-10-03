"""Catálogo maestro de referencias semanales de insumos Biofloc."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.referencia_aplicacion_biofloc import (
    ReferenciaAplicacionBioflocCreate,
    ReferenciaAplicacionBioflocOut,
    ReferenciaAplicacionBioflocUpdate,
)
from app.services.auth_service import get_current_user
from app.services import referencia_aplicacion_biofloc_service as svc

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR"}


def _require_roles(usuario: Usuario, db: Session, permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in permitidos:
        raise HTTPException(status_code=403, detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado")


@router.get("/", response_model=list[ReferenciaAplicacionBioflocOut])
def listar(especie_id: int | None = None, semana: int | None = None, solo_activos: bool = False,
           db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar(db, especie_id=especie_id, semana=semana, solo_activos=solo_activos)


@router.get("/{referencia_id}", response_model=ReferenciaAplicacionBioflocOut)
def obtener(referencia_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener(db, referencia_id)


@router.post("/", response_model=ReferenciaAplicacionBioflocOut, status_code=status.HTTP_201_CREATED)
def crear(data: ReferenciaAplicacionBioflocCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear(db, data, usuario_id=current_user.id)


@router.put("/{referencia_id}", response_model=ReferenciaAplicacionBioflocOut)
def actualizar(referencia_id: int, data: ReferenciaAplicacionBioflocUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar(db, referencia_id, data, usuario_id=current_user.id)
