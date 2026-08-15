from sqlalchemy import BigInteger, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from app.core.database import Base


class DetalleCompra(Base):
    """Detalle individual de una compra (1 detalle = 1 movimiento entrada inventario)."""
    __tablename__ = "detalles_compra"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="detalles_compra_cantidad_check"),
        CheckConstraint("precio_unitario >= 0", name="detalles_compra_precio_unitario_check"),
        CheckConstraint("subtotal >= 0", name="detalles_compra_subtotal_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    compra_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    compra = relationship("Compra", back_populates="detalles")
    producto = relationship("Producto")
