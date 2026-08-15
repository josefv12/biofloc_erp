"""
Servicio para operaciones CRUD de estanques.

Reglas de negocio aplicadas:
- estado_id debe existir en estados_estanque.
- La auditoría registra INSERT en creación y UPDATE en modificación.
- No se aplica DELETE físico; se usa activo=False para desactivar.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.estanque import Estanque, EstadoEstanque
from app.models.auditoria import Auditoria
from app.schemas.estanque import EstanqueCreate, EstanqueUpdate


def _get_estado_or_404(db: Session, estado_id: int) -> EstadoEstanque:
    estado = db.query(EstadoEstanque).filter(EstadoEstanque.id == estado_id).first()
    if not estado:
        raise HTTPException(status_code=404, detail=f"estado_estanque id={estado_id} no existe")
    return estado


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    entrada = Auditoria(
        usuario_id=usuario_id,
        tabla="estanques",
        registro_id=registro_id,
        accion=accion,
        detalle=detalle,
    )
    db.add(entrada)


def listar_estanques(db: Session, solo_activos: bool = True) -> list[Estanque]:
    q = db.query(Estanque)
    if solo_activos:
        q = q.filter(Estanque.activo == True)
    return q.order_by(Estanque.codigo).all()


def obtener_estanque(db: Session, estanque_id: int) -> Estanque:
    e = db.query(Estanque).filter(Estanque.id == estanque_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estanque no encontrado")
    return e


def crear_estanque(db: Session, data: EstanqueCreate, usuario_id: int) -> Estanque:
    # Verificar estado válido
    _get_estado_or_404(db, data.estado_id)

    # Verificar código único
    existe = db.query(Estanque).filter(Estanque.codigo == data.codigo).first()
    if existe:
        raise HTTPException(status_code=409, detail=f"Ya existe un estanque con código '{data.codigo}'")

    nuevo = Estanque(**data.model_dump())
    db.add(nuevo)
    db.flush()  # para obtener el id sin commit

    _registrar_auditoria(db, usuario_id, "INSERT", nuevo.id, {"codigo": data.codigo, "nombre": data.nombre})
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_estanque(db: Session, estanque_id: int, data: EstanqueUpdate, usuario_id: int) -> Estanque:
    estanque = obtener_estanque(db, estanque_id)

    if data.estado_id is not None:
        _get_estado_or_404(db, data.estado_id)

    cambios = data.model_dump(exclude_none=True)
    for campo, valor in cambios.items():
        setattr(estanque, campo, valor)

    _registrar_auditoria(db, usuario_id, "UPDATE", estanque.id, cambios)
    db.commit()
    db.refresh(estanque)
    return estanque
