from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.acondicionamiento_biofloc_estanque import AcondicionamientoBioflocEstanqueCreate, AcondicionamientoBioflocEstanqueOut
from app.services.auth_service import get_current_user
from app.services import acondicionamiento_biofloc_estanque_service as svc
from app.services.movimiento_inventario_service import obtener_stock_producto

router = APIRouter()
ROLES = {"ADMINISTRADOR", "TECNICO", "OPERARIO"}

def require_role(usuario: Usuario, db: Session):
    from app.models.rol import Rol
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not rol or rol.nombre not in ROLES:
        raise HTTPException(status_code=403, detail="Rol no autorizado para acondicionamiento Biofloc")

@router.get("/{estanque_id}", response_model=list[AcondicionamientoBioflocEstanqueOut])
def listar(estanque_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    require_role(current_user, db)
    return svc.listar(db, estanque_id)

@router.post("/", response_model=AcondicionamientoBioflocEstanqueOut, status_code=status.HTTP_201_CREATED)
def crear(data: AcondicionamientoBioflocEstanqueCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    require_role(current_user, db)
    row = svc.crear(db, data, current_user.id)
    result = AcondicionamientoBioflocEstanqueOut.model_validate(row)
    if data.producto_id and data.cantidad and data.cantidad > 0:
        result.stock_restante = float(obtener_stock_producto(db, data.producto_id))
    return result
