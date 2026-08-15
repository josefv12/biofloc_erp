from sqlalchemy import BigInteger, String, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class Producto(Base):
    """Catálogo maestro de productos del inventario."""
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categorias_inventario.id"), nullable=False)
    unidad_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidades.id"), nullable=False)
    stock_minimo: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, server_default=text("0"))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    categoria = relationship("CategoriaInventario")
    unidad = relationship("Unidad")
