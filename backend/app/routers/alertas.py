"""
Router /api/v1/alertas
Alarmas de inventario sobre vista_stock_productos (solo lectura).

RBAC:
  GET /stock-bajo            : ADMINISTRADOR, TECNICO, OPERARIO
  GET /stock-bajo/{id}       : ADMINISTRADOR, TECNICO, OPERARIO
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.alarma import AlarmaStockOut, CLASIFICACIONES
from app.services.auth_service import get_current_user
from app.services import alarma_service as svc

router = APIRouter()

ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    from fastapi import HTTPException
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/stock-bajo", response_model=list[AlarmaStockOut])
def listar_stock_bajo(
    solo_activos: bool = True,
    categoria_id: Optional[int] = None,
    unidad: Optional[str] = None,
    producto_id: Optional[int] = None,
    incluir_normal: bool = False,
    clasificacion: Optional[list[str]] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    if clasificacion:
        unknown = [c for c in clasificacion if c not in CLASIFICACIONES]
        if unknown:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=f"Clasificaciones inválidas: {unknown}. Validas: {list(CLASIFICACIONES)}")
    return svc.listar_alertas_stock_bajo(
        db,
        solo_activos=solo_activos,
        categoria_id=categoria_id,
        unidad=unidad,
        producto_id=producto_id,
        incluir_normal=incluir_normal,
        clasificacion=clasificacion,
    )


@router.get("/stock-bajo/{producto_id}", response_model=AlarmaStockOut)
def detalle_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_alerta_producto(db, producto_id)
