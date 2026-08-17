"""
Router para /api/v1/lotes

Roles y permisos:
- ADMINISTRADOR : GET, POST, PUT
- TECNICO       : GET, POST, PUT
- OPERARIO      : GET (solo consulta)

Decisión de diseño: No se expone DELETE físico.
Para finalizar/cancelar un lote se usa PUT cambiando estado_id.
La restricción de 1 solo lote ACTIVO por estanque la maneja el trigger
PostgreSQL trg_validar_lote_activo (el servicio convierte la excepción a HTTP 409).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.lote import LoteCreate, LoteUpdate, LoteOut
from app.services.auth_service import get_current_user
from app.services import lote_service as svc

router = APIRouter()


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(status_code=403, detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado")


@router.get("/", response_model=list[LoteOut], summary="Listar lotes")
def listar(
    estanque_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.listar_lotes(db, estanque_id)


@router.get("/{lote_id}", response_model=LoteOut, summary="Obtener lote")
def obtener(
    lote_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO", "OPERARIO"})
    return svc.obtener_lote(db, lote_id)


@router.post("/", response_model=LoteOut, status_code=201, summary="Crear lote")
def crear(
    data: LoteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO"})
    return svc.crear_lote(db, data, current_user.id)


@router.put("/{lote_id}", response_model=LoteOut, summary="Actualizar lote")
def actualizar(
    lote_id: int,
    data: LoteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, {"ADMINISTRADOR", "TECNICO"})
    return svc.actualizar_lote(db, lote_id, data, current_user.id)
