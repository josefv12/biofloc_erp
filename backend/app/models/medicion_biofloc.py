from sqlalchemy import BigInteger, Numeric, String, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

class MedicionBiofloc(Base):
    """Registro de Biofloc asociado a un lote o a un estanque en pre-siembra."""
    __tablename__ = "mediciones_biofloc"
    __table_args__ = (
        CheckConstraint("volumen_sedimentable >= 0", name="mediciones_biofloc_volumen_check"),
        CheckConstraint("relacion_cn IS NULL OR relacion_cn >= 0", name="mediciones_biofloc_relacion_cn_check"),
        CheckConstraint(
            "(lote_id IS NOT NULL AND estanque_id IS NULL) OR (lote_id IS NULL AND estanque_id IS NOT NULL)",
            name="mediciones_biofloc_contexto_check",
        ),
        Index("idx_mediciones_biofloc_lote_fecha", "lote_id", "fecha_hora"),
        Index("idx_mediciones_biofloc_estanque_fecha", "estanque_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=True)
    estanque_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("estanques.id"), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    volumen_sedimentable: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default="mL/L")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    relacion_cn: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    lote = relationship("Lote")
    estanque = relationship("Estanque")
    registrador = relationship("Usuario")
