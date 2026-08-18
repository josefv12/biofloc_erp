"""Router GET /api/v1/analisis

Núcleo analítico V1. Solo lectura.
RBAC: GET ADMINISTRADOR, TECNICO, OPERARIO.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.analisis import AnalisisLoteCompletoOut, ComparativoEstanquesOut
from app.services.auth_service import get_current_user
from app.services import analisis_service as svc

router = APIRouter()
ROLES_LECTURA = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{rol.nombre if rol else '?'}' no autorizado para esta operación",
        )


@router.get("/lotes/{lote_id}", response_model=AnalisisLoteCompletoOut)
def analizar_lote(
    lote_id: int,
    fecha_desde: Optional[date] = Query(
        None, description="Recorta solo las series devueltas; los indicadores no cambian."
    ),
    fecha_hasta: Optional[date] = Query(
        None, description="Recorta solo las series devueltas; los indicadores no cambian."
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_LECTURA)
    return svc.analizar_lote(db, lote_id, fecha_desde, fecha_hasta)


@router.get("/estanques", response_model=ComparativoEstanquesOut)
def comparativo_estanques(
    solo_activos: bool = Query(True, description="Solo estanques activos."),
    estanque_id: Optional[int] = Query(None, gt=0, description="Limita la comparación a un estanque."),
    incluir_historial: bool = Query(
        False, description="Incluye ciclos históricos calculados por el mismo motor."
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Comparativo por estanque con el lote activo de cada uno (nivel granja)."""
    _require_roles(current_user, db, ROLES_LECTURA)
    if incluir_historial and estanque_id is None:
        raise HTTPException(
            status_code=422,
            detail="incluir_historial requiere estanque_id para limitar el payload",
        )
    return svc.comparativo_estanques(
        db,
        solo_activos=solo_activos,
        estanque_id=estanque_id,
        incluir_historial=incluir_historial,
    )
