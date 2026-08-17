"""
Biofloc ERP V1 - Configuración centralizada
Todas las variables de entorno se leen desde aquí.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación leída desde variables de entorno."""

    # --- Aplicación ---
    app_name: str = "Biofloc ERP"
    app_version: str = "1.0.0"
    app_env: str = "development"
    app_debug: bool = False
    # None = docs según APP_ENV (off en production). True/False fuerza ENABLE_DOCS.
    enable_docs: Optional[bool] = None

    # --- Base de datos ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "biofloc_erp"
    postgres_user: str = "biofloc_user"
    postgres_password: str = ""

    # --- JWT Authentication ---
    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_no_vacio(cls, v: str) -> str:
        if v is None or not str(v).strip():
            raise ValueError(
                "JWT_SECRET_KEY es obligatorio y no puede estar vacío. "
                "Defínalo en el entorno o en .env."
            )
        return v

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return bool(self.enable_docs)
        return self.app_env.strip().lower() != "production"

    @property
    def database_url(self) -> str:
        """Construye la URL de conexión a PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retorna la instancia singleton de Settings.
    El decorador lru_cache asegura que .env se lee una sola vez.
    """
    return Settings()
