from sqlalchemy import BigInteger, String, Numeric, Date, DateTime, Text, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from decimal import Decimal
from app.core.database import Base


class Compra(Base):
    """Registro maestro de compras (inmutable después de creado)."""
    __tablename__ = "compras"
    __table_args__ = (
        CheckConstraint("total >= 0", name="compras_total_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default=text("0"))
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan")
    registrador = relationship("Usuario")
