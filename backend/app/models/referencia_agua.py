from sqlalchemy import BigInteger, Numeric, Text, Boolean, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class ReferenciaAgua(Base):
    """Rangos y parámetros de referencia de agua por especie y etapa productiva."""
    __tablename__ = "referencias_agua"
    __table_args__ = (
        CheckConstraint(
            "valor_minimo IS NULL OR valor_maximo IS NULL OR valor_minimo <= valor_maximo",
            name="referencias_agua_valor_check"
        ),
        UniqueConstraint(
            "especie_id", "etapa_productiva_id", "parametro_id",
            name="referencias_agua_especie_etapa_parametro_key"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    especie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("especies.id"), nullable=False)
    etapa_productiva_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("etapas_productivas.id"), nullable=False)
    parametro_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("parametros_agua.id"), nullable=False)
    valor_minimo: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    valor_maximo: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    especie = relationship("Especie")
    etapa_productiva = relationship("EtapaProductiva")
    parametro = relationship("ParametroAgua")
