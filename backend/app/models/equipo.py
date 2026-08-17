from sqlalchemy import BigInteger, String, Numeric, Text, Date, DateTime, Boolean, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from app.core.database import Base


class TipoEquipo(Base):
    __tablename__ = "tipos_equipo"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EstadoEquipo(Base):
    __tablename__ = "estados_equipo"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Equipo(Base):
    __tablename__ = "equipos"
    __table_args__ = (
        CheckConstraint(
            "valor_adquisicion IS NULL OR valor_adquisicion >= 0",
            name="equipos_valor_adquisicion_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_equipo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_equipo.id"), nullable=False)
    estado_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estados_equipo.id"), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(80), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_adquisicion: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_adquisicion: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    tipo = relationship("TipoEquipo")
    estado = relationship("EstadoEquipo")
