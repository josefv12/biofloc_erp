from sqlalchemy import BigInteger, String, Numeric, DateTime, Text, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from app.core.database import Base


class MovimientoInventario(Base):
    """Movimientos históricos de inventario (INMUTABLES: sin PUT ni DELETE)."""
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="movimientos_inventario_cantidad_check"),
        CheckConstraint(
            "costo_unitario IS NULL OR costo_unitario >= 0",
            name="movimientos_inventario_costo_unitario_check",
        ),
        CheckConstraint(
            "costo_total IS NULL OR costo_total >= 0",
            name="movimientos_inventario_costo_total_check",
        ),
        Index("idx_movimientos_producto_fecha", "producto_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    producto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("productos.id"), nullable=False)
    tipo_movimiento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tipos_movimiento_inventario.id"), nullable=False
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    referencia_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    referencia_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    costo_total: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    producto = relationship("Producto")
    tipo_movimiento = relationship("TipoMovimientoInventario")
    registrador = relationship("Usuario")
