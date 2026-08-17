from sqlalchemy import BigInteger, String, Numeric, Text, DateTime, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from app.core.database import Base


class Falla(Base):
    __tablename__ = "fallas"
    __table_args__ = (
        CheckConstraint("costo >= 0", name="fallas_costo_check"),
        Index("idx_fallas_equipo_fecha", "equipo_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("equipos.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    impacto: Mapped[str | None] = mapped_column(String(100), nullable=True)
    solucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default=text("0"))
    registrada_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    equipo = relationship("Equipo")
    registrador = relationship("Usuario")
