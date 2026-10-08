from sqlalchemy import BigInteger, Numeric, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

class MedicionAgua(Base):
    """Registro de parámetros de agua asociado a un lote o a un estanque en pre-siembra."""
    __tablename__ = "mediciones_agua"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="mediciones_agua_valor_check"),
        CheckConstraint(
            "(lote_id IS NOT NULL AND estanque_id IS NULL) OR (lote_id IS NULL AND estanque_id IS NOT NULL)",
            name="mediciones_agua_contexto_check",
        ),
        Index("idx_mediciones_agua_lote_fecha", "lote_id", "fecha_hora"),
        Index("idx_mediciones_agua_estanque_fecha", "estanque_id", "fecha_hora"),
        Index("idx_mediciones_agua_parametro", "parametro_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=True)
    estanque_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("estanques.id"), nullable=True)
    parametro_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parametros_agua.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    lote = relationship("Lote")
    estanque = relationship("Estanque")
    parametro = relationship("ParametroAgua")
    registrador = relationship("Usuario")
