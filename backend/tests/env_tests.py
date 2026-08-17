"""
Credenciales de laboratorio para suites HTTP.

Los secretos se leen de variables de entorno (backend/.env).
No hardcodear passwords aquí.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(
            f"Falta la variable de entorno {name}. Defínala en backend/.env"
        )
    return value


ADMIN_USER = os.environ.get("TEST_ADMIN_CORREO", "admin@biofloc.com")
ADMIN_PASS = _require_env("TEST_ADMIN_PASSWORD")
TECNICO_USER = os.environ.get("TEST_TECNICO_CORREO", "tecnico_test@biofloc.com")
TECNICO_PASS = _require_env("TEST_TECNICO_PASSWORD")
OPERARIO_USER = os.environ.get("TEST_OPERARIO_CORREO", "operario_test@biofloc.com")
OPERARIO_PASS = _require_env("TEST_OPERARIO_PASSWORD")

ADM_CRED = (ADMIN_USER, ADMIN_PASS)
TEC_CRED = (TECNICO_USER, TECNICO_PASS)
OPE_CRED = (OPERARIO_USER, OPERARIO_PASS)

DB_CONF = dict(
    host=os.environ.get("TEST_DB_HOST", "localhost"),
    port=int(os.environ.get("TEST_DB_PORT", "5432")),
    dbname=os.environ.get("TEST_DB_NAME", "biofloc_erp"),
    user=os.environ.get("TEST_DB_USER", "postgres"),
    password=_require_env("TEST_DB_PASSWORD"),
)
