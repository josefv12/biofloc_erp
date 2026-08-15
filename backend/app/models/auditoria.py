from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Any

from app.core.database import Base
from app.models.usuario import Usuario

class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=True)
    tabla: Mapped[str] = mapped_column(String(100), nullable=False)
    registro_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relación con Usuario
    usuario: Mapped["Usuario | None"] = relationship("Usuario")

    __table_args__ = (
        CheckConstraint("accion IN ('INSERT', 'UPDATE', 'DELETE')", name="auditoria_accion_check"),
        Index("idx_auditoria_tabla_registro", "tabla", "registro_id"),
        Index("idx_auditoria_usuario_fecha", "usuario_id", "fecha_hora"),
    )
