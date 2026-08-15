from sqlalchemy import BigInteger, String, Numeric, Text, Date, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from app.core.database import Base


class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (
        CheckConstraint("valor > 0", name="gastos_valor_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categorias_gasto.id"), nullable=False)
    lote_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    categoria = relationship("CategoriaGasto")
    lote = relationship("Lote")
    registrador = relationship("Usuario")
