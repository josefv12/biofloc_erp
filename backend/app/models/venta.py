from sqlalchemy import BigInteger, String, Numeric, Text, Date, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from app.core.database import Base


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ventas_total_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    cliente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, server_default=text("0"))
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    registrador = relationship("Usuario")


class DetalleVenta(Base):
    __tablename__ = "detalles_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="detalles_venta_cantidad_check"),
        CheckConstraint("precio_unitario >= 0", name="detalles_venta_precio_unitario_check"),
        CheckConstraint("subtotal >= 0", name="detalles_venta_subtotal_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)

    venta = relationship("Venta", back_populates="detalles")
    lote = relationship("Lote")
