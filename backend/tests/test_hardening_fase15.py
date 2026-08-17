#!/usr/bin/env python3
"""FASE 15 — JWT, health/docs y configuración. Prefijo [TEST_HARDENING].

No imprime secretos. Requiere servidor en :8000 y variables TEST_* en .env.
"""
import os
import sys
import io
import pathlib
import requests
from pydantic import ValidationError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS,
)

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings  # noqa: E402

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_HARDENING]"
R = []


def log(n, name, ok, d=""):
    icon = "[OK]" if ok else "[FAIL]"
    n_str = f"{n:02d}" if isinstance(n, int) else str(n)
    m = f"  {icon} [{n_str}] {name}"
    if d:
        m += f"\n       -> {d}"
    print(m)
    R.append((n, name, ok, d))


def login(c, p):
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": c, "password": p})
    return r.json().get("access_token") if r.status_code == 200 else None


def main():
    print(f"\n{PREF} INICIO\n")

    try:
        Settings(_env_file=None, jwt_secret_key="")
        ok_empty = False
        d_empty = "Settings acepto secreto vacio"
    except (ValidationError, ValueError):
        ok_empty = True
        d_empty = "ValidationError"
    log(1, "Settings JWT_SECRET_KEY vacio falla", ok_empty, d_empty)

    try:
        Settings(_env_file=None, jwt_secret_key="   ")
        ok_ws = False
        d_ws = "Settings acepto whitespace"
    except (ValidationError, ValueError):
        ok_ws = True
        d_ws = "ValidationError"
    log(2, "Settings JWT_SECRET_KEY whitespace falla", ok_ws, d_ws)

    dummy = "fase15-test-only-not-a-real-secret"
    prod = Settings(_env_file=None, jwt_secret_key=dummy, app_env="production")
    dev = Settings(_env_file=None, jwt_secret_key=dummy, app_env="development")
    forced = Settings(_env_file=None, jwt_secret_key=dummy, app_env="production", enable_docs=True)
    log(3, "docs off en production, on en development, ENABLE_DOCS fuerza on",
        (prod.docs_enabled is False) and (dev.docs_enabled is True) and (forced.docs_enabled is True))

    r = requests.get(f"{BASE}/health")
    body = r.json() if r.status_code == 200 else {}
    ok = (
        r.status_code == 200
        and body.get("api") == "ok"
        and body.get("database") == "ok"
        and "database_error" not in body
    )
    log(4, "GET /health api+db=ok sin database_error", ok, f"keys={sorted(body.keys())}")

    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(5, "Login ADMIN", bool(tok_a))
    log(6, "Login TECNICO", bool(tok_t))
    log(7, "Login OPERARIO", bool(tok_o))

    r = requests.get(f"{BASE}/api/v1/estanques/")
    log(8, "GET protegido sin JWT -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.get(
        f"{BASE}/api/v1/estanques/",
        headers={"Authorization": "Bearer token-invalido"},
    )
    log(9, "GET protegido token invalido -> 401", r.status_code == 401, f"status={r.status_code}")

    r = requests.get(
        f"{BASE}/api/v1/estanques/",
        headers={"Authorization": f"Bearer {tok_a}"},
    ) if tok_a else type("R", (), {"status_code": 0})()
    log(10, "GET protegido ADMIN 200", r.status_code == 200, f"status={r.status_code}")

    r = requests.get(f"{BASE}/docs")
    log(11, "GET /docs disponible en development", r.status_code == 200, f"status={r.status_code}")

    r = requests.get(f"{BASE}/openapi.json")
    log(12, "GET /openapi.json disponible en development", r.status_code == 200, f"status={r.status_code}")

    app_dir = BACKEND / "app"
    utcnow_hits = []
    hardcoded_entrada = False
    for p in app_dir.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if "datetime.utcnow(" in txt:
            utcnow_hits.append(str(p.relative_to(BACKEND)))
        if p.name == "compra_service.py" and "TIPO_MOV_ENTRADA_ID" in txt:
            hardcoded_entrada = True
    log(13, "datetime.utcnow() ausente en backend/app", utcnow_hits == [], f"hits={utcnow_hits}")
    log(14, "compra_service sin TIPO_MOV_ENTRADA_ID", not hardcoded_entrada)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2


if __name__ == "__main__":
    os.chdir(str(BACKEND))
    sys.exit(main())
