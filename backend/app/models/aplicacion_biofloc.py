from sqlalchemy import BigInteger, Numeric, String, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base

class AplicacionBiofloc(Base):
    """Registro de aplicaciones/tratamientos Biofloc en un lote."""
    __tablename__ = "aplicaciones_biofloc"
    __table_args__ = (
        CheckConstraint("cantidad IS NULL OR cantidad >= 0", name="aplicaciones_biofloc_cantidad_check"),
        Index("idx_aplicaciones_biofloc_lote_fecha", "lote_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    tipo_aplicacion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_aplicacion_biofloc.id"), nullable=False)
    # producto_id no tiene FK en el DDL; es BIGINT NULL libre (Inventario no implementado)
    producto_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote = relationship("Lote")
    tipo_aplicacion = relationship("TipoAplicacionBiofloc")
    registrador = relationship("Usuario")
