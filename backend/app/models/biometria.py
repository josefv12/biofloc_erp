from sqlalchemy import BigInteger, Integer, Numeric, String, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.lote import Lote
    from app.models.usuario import Usuario


class Biometria(Base):
    """Registro de biometría o muestreo de un lote."""
    __tablename__ = "biometrias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad_muestra: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_total_muestra: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    talla_promedio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    unidad_talla: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote: Mapped["Lote"] = relationship("Lote")
    registrador: Mapped["Usuario"] = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("cantidad_muestra > 0", name="biometrias_cantidad_muestra_check"),
        CheckConstraint("peso_total_muestra > 0", name="biometrias_peso_total_muestra_check"),
        CheckConstraint("talla_promedio >= 0", name="biometrias_talla_promedio_check"),
        Index("idx_biometrias_lote_fecha", "lote_id", "fecha_hora"),
    )
