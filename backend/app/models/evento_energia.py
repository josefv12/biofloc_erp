from sqlalchemy import BigInteger, String, Integer, Text, DateTime, Boolean, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class EventoEnergia(Base):
    __tablename__ = "eventos_energia"
    __table_args__ = (
        CheckConstraint(
            "fecha_hora_fin IS NULL OR fecha_hora_fin >= fecha_hora_inicio",
            name="eventos_energia_check",
        ),
        CheckConstraint(
            "duracion_minutos IS NULL OR duracion_minutos >= 0",
            name="eventos_energia_duracion_minutos_check",
        ),
        CheckConstraint(
            "respaldo_activado = FALSE OR equipo_respaldo_id IS NOT NULL",
            name="eventos_energia_check1",
        ),
        Index("idx_eventos_energia_fecha", "fecha_hora_inicio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha_hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_hora_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracion_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'CORTE'"))
    respaldo_activado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    equipo_respaldo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("equipos.id"), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    equipo_respaldo = relationship("Equipo")
    registrador = relationship("Usuario")
