from sqlalchemy import BigInteger, Numeric, String, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

class MedicionBiofloc(Base):
    """Registro de mediciones de Biofloc (volumen sedimentable y relación C:N) en un lote."""
    __tablename__ = "mediciones_biofloc"
    __table_args__ = (
        CheckConstraint("volumen_sedimentable >= 0", name="mediciones_biofloc_volumen_check"),
        CheckConstraint("relacion_cn IS NULL OR relacion_cn >= 0", name="mediciones_biofloc_relacion_cn_check"),
        Index("idx_mediciones_biofloc_lote_fecha", "lote_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    volumen_sedimentable: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default="mL/L")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    relacion_cn: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote = relationship("Lote")
    registrador = relationship("Usuario")
