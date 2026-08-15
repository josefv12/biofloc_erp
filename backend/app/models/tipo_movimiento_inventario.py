from sqlalchemy import BigInteger, String, SmallInteger, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TipoMovimientoInventario(Base):
    """Clasificación de movimientos de inventario (ENTRADA, SALIDA, etc.)."""
    __tablename__ = "tipos_movimiento_inventario"
    __table_args__ = (
        CheckConstraint("afecta_stock IN (-1, 1)", name="tipos_movimiento_inventario_afecta_stock_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    afecta_stock: Mapped[int] = mapped_column(SmallInteger, nullable=False)
