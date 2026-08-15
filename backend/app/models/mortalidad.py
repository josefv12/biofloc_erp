from sqlalchemy import BigInteger, Integer, String, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.lote import Lote
    from app.models.usuario import Usuario


class Mortalidad(Base):
    """Registro de mortalidad de un lote."""
    __tablename__ = "mortalidades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    causa: Mapped[str | None] = mapped_column(String(150), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote: Mapped["Lote"] = relationship("Lote")
    registrador: Mapped["Usuario"] = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="mortalidades_cantidad_check"),
        Index("idx_mortalidades_lote_fecha", "lote_id", "fecha_hora"),
    )
