"""
Router /api/v1/categorias-inventario
RBAC:
  GET : 3 roles
  POST/PUT: ADMINISTRADOR + TECNICO
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.categoria_inventario import (
    CategoriaInventarioCreate, CategoriaInventarioUpdate, CategoriaInventarioOut
)
from app.services.auth_service import get_current_user
from app.services import categoria_inventario_service as svc

router = APIRouter()

ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}
ROLES_ESCRITURA = {"ADMINISTRADOR", "TECNICO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/", response_model=list[CategoriaInventarioOut])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.listar_categorias_inventario(db, solo_activos=solo_activos)


@router.get("/{categoria_id}", response_model=CategoriaInventarioOut)
def obtener(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.obtener_categoria_inventario(db, categoria_id)


@router.post("/", response_model=CategoriaInventarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: CategoriaInventarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.crear_categoria_inventario(db, data, usuario_id=current_user.id)


@router.put("/{categoria_id}", response_model=CategoriaInventarioOut)
def actualizar(
    categoria_id: int,
    data: CategoriaInventarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_ESCRITURA)
    return svc.actualizar_categoria_inventario(db, categoria_id, data, usuario_id=current_user.id)
