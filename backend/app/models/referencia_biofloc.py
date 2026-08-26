from sqlalchemy import BigInteger, Numeric, String, Text, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

INDICADORES_BIOFLOC = ("VOLUMEN_SEDIMENTABLE", "RELACION_CN")


class ReferenciaBiofloc(Base):
    """Rangos y objetivo de Biofloc por especie y etapa. Sin valores semilla."""

    __tablename__ = "referencias_biofloc"
    __table_args__ = (
        CheckConstraint(
            "indicador IN ('VOLUMEN_SEDIMENTABLE', 'RELACION_CN')",
            name="referencias_biofloc_indicador_check",
        ),
        CheckConstraint(
            "valor_minimo IS NULL OR valor_maximo IS NULL OR valor_minimo <= valor_maximo",
            name="referencias_biofloc_rango_check",
        ),
        UniqueConstraint(
            "especie_id",
            "etapa_productiva_id",
            "indicador",
            name="referencias_biofloc_especie_etapa_indicador_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    especie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("especies.id"), nullable=False)
    etapa_productiva_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("etapas_productivas.id"), nullable=False
    )
    indicador: Mapped[str] = mapped_column(String(40), nullable=False)
    valor_minimo: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    valor_objetivo: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    valor_maximo: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    unidad: Mapped[str | None] = mapped_column(String(30), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    especie = relationship("Especie")
    etapa_productiva = relationship("EtapaProductiva")
