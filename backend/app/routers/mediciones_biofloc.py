"""
Router para /api/v1/mediciones-biofloc
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.medicion_biofloc import MedicionBioflocCreate, MedicionBioflocOut
from app.services.auth_service import get_current_user
from app.services import medicion_biofloc_service as svc

router = APIRouter()
ROLES_PERMITIDOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}

def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(status_code=403, detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación")

@router.get("/", response_model=list[MedicionBioflocOut])
def listar(lote_id: Optional[int] = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.listar_mediciones_biofloc(db, lote_id=lote_id)

@router.get("/{medicion_id}", response_model=MedicionBioflocOut)
def obtener(medicion_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.obtener_medicion_biofloc(db, medicion_id)

@router.post("/", response_model=MedicionBioflocOut, status_code=status.HTTP_201_CREATED)
def crear(data: MedicionBioflocCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    _require_roles(current_user, db, ROLES_PERMITIDOS)
    return svc.crear_medicion_biofloc(db, data, usuario_id=current_user.id)
