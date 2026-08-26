"""Router /api/v1/referencias-biofloc

Catálogo maestro. Sin valores semilla.

RBAC:
- GET  ADMINISTRADOR, TECNICO, OPERARIO
- POST/PUT ADMINISTRADOR
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.referencia_biofloc import (
    ReferenciaBioflocCreate,
    ReferenciaBioflocOut,
    ReferenciaBioflocUpdate,
)
from app.services.auth_service import get_current_user
from app.services import referencia_biofloc_service as svc

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


@router.get("/", response_model=list[ReferenciaBioflocOut])
def listar(
    especie_id: Optional[int] = None,
    etapa_productiva_id: Optional[int] = None,
    indicador: Optional[str] = None,
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_referencias_biofloc(
        db,
        especie_id=especie_id,
        etapa_productiva_id=etapa_productiva_id,
        indicador=indicador,
        solo_activos=solo_activos,
    )


@router.get("/{referencia_id}", response_model=ReferenciaBioflocOut)
def obtener(
    referencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_referencia_biofloc(db, referencia_id)


@router.post("/", response_model=ReferenciaBioflocOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: ReferenciaBioflocCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_referencia_biofloc(db, data, usuario_id=current_user.id)


@router.put("/{referencia_id}", response_model=ReferenciaBioflocOut)
def actualizar(
    referencia_id: int,
    data: ReferenciaBioflocUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_referencia_biofloc(db, referencia_id, data, usuario_id=current_user.id)
