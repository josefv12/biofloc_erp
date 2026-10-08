from sqlalchemy import BigInteger, Numeric, String, DateTime, Date, Boolean, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional
from app.core.database import Base

class AcondicionamientoBioflocEstanque(Base):
    __tablename__ = "acondicionamientos_biofloc_estanque"
    __table_args__ = (
        CheckConstraint("cantidad IS NULL OR cantidad >= 0", name="acond_biofloc_cantidad_check"),
        Index("idx_acond_biofloc_lote_fecha", "lote_id", "fecha_hora"),
        Index("idx_acond_biofloc_estanque_fecha", "estanque_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes.id"), nullable=False)
    estanque_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estanques.id"), nullable=False)
    tipo_aplicacion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_aplicacion_biofloc.id"), nullable=False)
    producto_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("productos.id"), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_siembra_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    unidad: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    aireacion_activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observaciones: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    registrado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    lote = relationship("Lote")
    estanque = relationship("Estanque")
    tipo_aplicacion = relationship("TipoAplicacionBiofloc")
    producto = relationship("Producto")
    registrador = relationship("Usuario")
