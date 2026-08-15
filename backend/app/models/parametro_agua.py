from sqlalchemy import BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class ParametroAgua(Base):
    """Catálogo maestro de parámetros de calidad de agua."""
    __tablename__ = "parametros_agua"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    unidad: Mapped[str] = mapped_column(String(30), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
