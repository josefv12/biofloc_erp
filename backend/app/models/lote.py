from sqlalchemy import BigInteger, SmallInteger, String, Integer, Numeric, Date, DateTime, Text, Boolean, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.estanque import Estanque


class Especie(Base):
    """Catálogo de especies cultivadas."""
    __tablename__ = "especies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre_comun: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    nombre_cientifico: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EtapaProductiva(Base):
    """Catálogo de etapas del ciclo productivo."""
    __tablename__ = "etapas_productivas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("orden > 0", name="etapas_productivas_orden_check"),
    )


class EstadoLote(Base):
    """Catálogo de estados posibles de un lote."""
    __tablename__ = "estados_lote"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Lote(Base):
    """Lote de producción activo en un estanque."""
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    estanque_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estanques.id"), nullable=False)
    especie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("especies.id"), nullable=False)
    etapa_productiva_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("etapas_productivas.id"), nullable=False)
    estado_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("estados_lote.id"), nullable=False)
    fecha_siembra: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_cierre: Mapped[date | None] = mapped_column(Date, nullable=True)
    cantidad_sembrada: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_inicial_promedio: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    # Relaciones
    estanque: Mapped["Estanque"] = relationship("Estanque")
    especie: Mapped["Especie"] = relationship("Especie")
    etapa_productiva: Mapped["EtapaProductiva"] = relationship("EtapaProductiva")
    estado: Mapped["EstadoLote"] = relationship("EstadoLote")

    __table_args__ = (
        CheckConstraint("cantidad_sembrada > 0", name="lotes_cantidad_sembrada_check"),
        CheckConstraint("peso_inicial_promedio IS NULL OR peso_inicial_promedio >= 0", name="lotes_peso_inicial_check"),
        CheckConstraint("fecha_cierre IS NULL OR fecha_cierre >= fecha_siembra", name="lotes_fecha_cierre_check"),
        Index("idx_lotes_estanque", "estanque_id"),
        Index("idx_lotes_estado", "estado_id"),
        Index("idx_lotes_especie", "especie_id"),
    )
