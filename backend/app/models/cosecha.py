from sqlalchemy import BigInteger, Integer, Numeric, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from app.core.database import Base

class Cosecha(Base):
    __tablename__ = "cosechas"
    __table_args__ = (
        CheckConstraint('peso_total > 0', name='cosechas_peso_total_check'),
        CheckConstraint('cantidad_peces > 0', name='cosechas_cantidad_peces_check'),
        CheckConstraint('peso_promedio IS NULL OR peso_promedio >= 0', name='cosechas_peso_promedio_check'),
        {"schema": "biofloc"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cantidad_peces: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_total: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    peso_promedio: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lote = relationship("Lote")
    registrador = relationship("Usuario")
