from sqlalchemy import BigInteger, String, DateTime, Text, ForeignKey, Index, CheckConstraint, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.lote import Lote
    from app.models.usuario import Usuario


class Alimentacion(Base):
    """Registro de alimentación de un lote."""
    __tablename__ = "alimentaciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False) # FK to productos(id), omitted relationship to avoid cascade model creation
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote: Mapped["Lote"] = relationship("Lote")
    registrador: Mapped["Usuario"] = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="alimentaciones_cantidad_check"),
        Index("idx_alimentaciones_lote_fecha", "lote_id", "fecha_hora"),
        Index("idx_alimentaciones_producto", "producto_id"),
    )
