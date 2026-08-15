from sqlalchemy import BigInteger, String, Numeric, Boolean, DateTime, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.lote import Lote


class EstadoEstanque(Base):
    """Catálogo de estados posibles de un estanque."""
    __tablename__ = "estados_estanque"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Estanque(Base):
    """Infraestructura física: estanques de cultivo."""
    __tablename__ = "estanques"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    diametro: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    profundidad: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    estado_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estados_estanque.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    estado: Mapped["EstadoEstanque"] = relationship("EstadoEstanque")

    __table_args__ = (
        CheckConstraint("diametro > 0", name="estanques_diametro_check"),
        CheckConstraint("profundidad > 0", name="estanques_profundidad_check"),
    )
