"""
Biofloc ERP V1 - Configuración de la base de datos
SQLAlchemy 2.x con sesiones gestionadas mediante generador de dependencias.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

# --- Motor de SQLAlchemy ---
engine = create_engine(
    settings.database_url,
    connect_args={"options": "-csearch_path=biofloc"},
    echo=settings.app_debug,       # Imprime SQL solo en modo debug
    pool_pre_ping=True,            # Verifica la conexión antes de usarla
    pool_size=5,
    max_overflow=10,
)

# --- Fábrica de sesiones ---
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# --- Base declarativa para futuros modelos ---
class Base(DeclarativeBase):
    """Clase base de la que heredarán todos los modelos SQLAlchemy."""
    pass


# --- Dependencia de FastAPI ---
def get_db() -> Generator:
    """
    Generador de sesiones de base de datos para inyección de dependencias.
    Garantiza que la sesión se cierra aunque ocurra una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
