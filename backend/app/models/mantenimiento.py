from sqlalchemy import BigInteger, String, Numeric, Text, Date, DateTime, Boolean, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from decimal import Decimal
from app.core.database import Base


class TipoMantenimiento(Base):
    __tablename__ = "tipos_mantenimiento"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"
    __table_args__ = (
        CheckConstraint("costo >= 0", name="mantenimientos_costo_check"),
        Index("idx_mantenimientos_equipo_fecha", "equipo_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("equipos.id"), nullable=False)
    tipo_mantenimiento_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_mantenimiento.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default=text("0"))
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    equipo = relationship("Equipo")
    tipo = relationship("TipoMantenimiento")
    registrador = relationship("Usuario")
