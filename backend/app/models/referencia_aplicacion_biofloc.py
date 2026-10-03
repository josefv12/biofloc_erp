from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


FASES_BIOFLOC = ("Inicio", "Levante", "Engorde")


class ReferenciaAplicacionBiofloc(Base):
    """Referencia semanal de consumo de insumos Biofloc para una especie."""
    __tablename__ = "referencias_aplicacion_biofloc"
    __table_args__ = (
        CheckConstraint("semana > 0", name="ref_aplicacion_biofloc_semana_check"),
        CheckConstraint("fase IN ('Inicio', 'Levante', 'Engorde')", name="ref_aplicacion_biofloc_fase_check"),
        CheckConstraint("cantidad_referencia >= 0", name="ref_aplicacion_biofloc_cantidad_check"),
        CheckConstraint("base_peces > 0", name="ref_aplicacion_biofloc_base_peces_check"),
        UniqueConstraint("especie_id", "semana", "producto_id", name="ref_aplicacion_biofloc_especie_semana_producto_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    especie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("especies.id"), nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    fase: Mapped[str] = mapped_column(String(40), nullable=False)
    producto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("productos.id"), nullable=False)
    cantidad_referencia: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    base_peces: Mapped[int] = mapped_column(Integer, nullable=False, default=1100)
    biomasa_objetivo_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    especie = relationship("Especie")
    producto = relationship("Producto")
