"""Router /api/v1/referencias-produccion

Catálogo maestro de producción. Tabla DDL existente; no se duplica.

RBAC:
- GET  ADMINISTRADOR, TECNICO, OPERARIO
- POST/PUT ADMINISTRADOR
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.referencia_produccion import (
    ReferenciaProduccionCreate,
    ReferenciaProduccionOut,
    ReferenciaProduccionUpdate,
)
from app.services.auth_service import get_current_user
from app.services import referencia_produccion_service as svc

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


@router.get("/", response_model=list[ReferenciaProduccionOut])
def listar(
    especie_id: Optional[int] = None,
    etapa_productiva_id: Optional[int] = None,
    semana: Optional[int] = None,
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_referencias_produccion(
        db,
        especie_id=especie_id,
        etapa_productiva_id=etapa_productiva_id,
        semana=semana,
        solo_activos=solo_activos,
    )


@router.get("/{referencia_id}", response_model=ReferenciaProduccionOut)
def obtener(
    referencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_referencia_produccion(db, referencia_id)


@router.post("/", response_model=ReferenciaProduccionOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: ReferenciaProduccionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_referencia_produccion(db, data, usuario_id=current_user.id)


@router.put("/{referencia_id}", response_model=ReferenciaProduccionOut)
def actualizar(
    referencia_id: int,
    data: ReferenciaProduccionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_referencia_produccion(
        db, referencia_id, data, usuario_id=current_user.id
    )
