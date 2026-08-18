from sqlalchemy import BigInteger, Integer, Numeric, Text, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class ReferenciaProduccion(Base):
    """Valores esperados por especie, etapa y rango de semana. Tabla DDL existente."""

    __tablename__ = "referencias_produccion"
    __table_args__ = (
        CheckConstraint("semana_desde >= 0", name="referencias_produccion_semana_desde_check"),
        CheckConstraint("semana_hasta >= semana_desde", name="referencias_produccion_semana_hasta_check"),
        CheckConstraint("peso_esperado_g IS NULL OR peso_esperado_g >= 0", name="referencias_produccion_peso_check"),
        CheckConstraint(
            "tasa_alimentacion_pct IS NULL OR tasa_alimentacion_pct >= 0",
            name="referencias_produccion_tasa_check",
        ),
        UniqueConstraint(
            "especie_id",
            "etapa_productiva_id",
            "semana_desde",
            "semana_hasta",
            name="referencias_produccion_especie_etapa_semana_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    especie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("especies.id"), nullable=False)
    etapa_productiva_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("etapas_productivas.id"), nullable=False)
    semana_desde: Mapped[int] = mapped_column(Integer, nullable=False)
    semana_hasta: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_esperado_g: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    tasa_alimentacion_pct: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    especie = relationship("Especie")
    etapa_productiva = relationship("EtapaProductiva")
