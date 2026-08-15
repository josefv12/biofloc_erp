from sqlalchemy import BigInteger, Numeric, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

class MedicionAgua(Base):
    """Registro de mediciones de parámetros de agua en un lote."""
    __tablename__ = "mediciones_agua"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="mediciones_agua_valor_check"),
        Index("idx_mediciones_agua_lote_fecha", "lote_id", "fecha_hora"),
        Index("idx_mediciones_agua_parametro", "parametro_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    parametro_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parametros_agua.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    lote = relationship("Lote")
    parametro = relationship("ParametroAgua")
    registrador = relationship("Usuario")
