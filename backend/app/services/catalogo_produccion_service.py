"""Consulta de etapas productivas y estados de lote/estanque. Sin escritura en esta fase."""
from sqlalchemy.orm import Session

from app.models.estanque import EstadoEstanque
from app.models.lote import EstadoLote, EtapaProductiva


def listar_etapas_productivas(db: Session, solo_activos: bool = False) -> list[EtapaProductiva]:
    q = db.query(EtapaProductiva)
    if solo_activos:
        q = q.filter(EtapaProductiva.activo.is_(True))
    return q.order_by(EtapaProductiva.orden.asc(), EtapaProductiva.nombre.asc()).all()


def listar_estados_lote(db: Session, solo_activos: bool = False) -> list[EstadoLote]:
    q = db.query(EstadoLote)
    if solo_activos:
        q = q.filter(EstadoLote.activo.is_(True))
    return q.order_by(EstadoLote.nombre.asc()).all()


def listar_estados_estanque(db: Session, solo_activos: bool = False) -> list[EstadoEstanque]:
    q = db.query(EstadoEstanque)
    if solo_activos:
        q = q.filter(EstadoEstanque.activo.is_(True))
    return q.order_by(EstadoEstanque.nombre.asc()).all()
