from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from decimal import Decimal
from sqlalchemy import text

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.venta import VentaCreate, VentaOut, DisponibilidadVentaOut
from app.services.auth_service import get_current_user
from app.services import venta_service as svc

router = APIRouter()

ROLES_TODOS = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}


def _require_roles(usuario: Usuario, db: Session, roles_permitidos: set[str]):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail="Rol no autorizado para esta operación",
        )


@router.get("/", response_model=list[VentaOut])
def listar(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    cliente: Optional[str] = None,
    lote_id: Optional[int] = None,
    registrado_por: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.listar_ventas(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        lote_id=lote_id,
        registrado_por=registrado_por,
    )


@router.get("/disponibilidad/{lote_id}", response_model=DisponibilidadVentaOut)
def disponibilidad(
    lote_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    row = db.execute(
        text("""
            SELECT lote_id, lote_codigo, cosechado_kg, vendido_kg, disponible_kg
            FROM biofloc.vista_disponibilidad_venta_lotes
            WHERE lote_id = :lote_id
        """),
        {"lote_id": lote_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return DisponibilidadVentaOut(
        lote_id=int(row["lote_id"]),
        lote_codigo=str(row["lote_codigo"]),
        cosechado_kg=Decimal(str(row["cosechado_kg"] or 0)),
        vendido_kg=Decimal(str(row["vendido_kg"] or 0)),
        disponible_kg=Decimal(str(row["disponible_kg"] or 0)),
    )


@router.get("/{venta_id}", response_model=VentaOut)
def obtener(
    venta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.obtener_venta(db, venta_id)


@router.post("/", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(current_user, db, ROLES_TODOS)
    return svc.crear_venta(db, data, usuario_id=current_user.id)
