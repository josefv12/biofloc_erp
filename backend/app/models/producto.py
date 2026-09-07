from sqlalchemy import BigInteger, String, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base


class Producto(Base):
    """Catálogo maestro de productos del inventario."""
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
        CheckConstraint("factor_conversion > 0", name="productos_factor_conversion_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categorias_inventario.id"), nullable=False)
    # unidad_id = unidad física interna usada por BD, movimientos y cálculos.
    unidad_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidades.id"), nullable=False)
    # unidad_comercial_id = unidad que el usuario ve/ingresa en la interfaz.
    unidad_comercial_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidades.id"), nullable=False)
    # Cantidad de unidades internas equivalentes a 1 unidad comercial.
    # Ej.: g -> kg = 1000; kg -> kg = 1.
    factor_conversion: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, server_default=text("1"))
    stock_minimo: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, server_default=text("0"))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    categoria = relationship("CategoriaInventario")
    unidad = relationship("Unidad", foreign_keys=[unidad_id])
    unidad_comercial = relationship("Unidad", foreign_keys=[unidad_comercial_id])
