from sqlalchemy import BigInteger, SmallInteger, String, Text, DateTime, Boolean, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class TipoAlarma(Base):
    __tablename__ = "tipos_alarma"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NivelAlarma(Base):
    __tablename__ = "niveles_alarma"
    __table_args__ = (
        CheckConstraint("prioridad > 0", name="niveles_alarma_prioridad_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    prioridad: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class EstadoAlarma(Base):
    __tablename__ = "estados_alarma"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Alarma(Base):
    __tablename__ = "alarmas"
    __table_args__ = (
        CheckConstraint(
            "fecha_atencion IS NULL OR fecha_atencion >= fecha_hora",
            name="alarmas_check",
        ),
        Index("idx_alarmas_fecha", "fecha_hora"),
        Index("idx_alarmas_estado", "estado_alarma_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo_alarma_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_alarma.id"), nullable=False)
    nivel_alarma_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("niveles_alarma.id"), nullable=False)
    estado_alarma_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estados_alarma.id"), nullable=False)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=True)
    equipo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("equipos.id"), nullable=True)
    evento_energia_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("eventos_energia.id"), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    atendida_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=True)
    fecha_atencion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    tipo = relationship("TipoAlarma")
    nivel = relationship("NivelAlarma")
    estado = relationship("EstadoAlarma")
    lote = relationship("Lote")
    equipo = relationship("Equipo")
    evento_energia = relationship("EventoEnergia")
    atendente = relationship("Usuario")
