#!/usr/bin/env python3
"""Regresión de encoding: catálogos API + fuentes UTF-8.

Falla si cualquier texto de catálogo o seed contiene mojibake típico.
No reescribe respuestas. No usa replace() en frontend.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import psycopg2
import requests

from env_tests import ADMIN_PASS, ADMIN_USER, DB_CONF

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
R: list[tuple[str, bool, str]] = []

# U+00C3 (Ã), U+00C2 (Â), U+FFFD, secuencia típica de UTF-8 mal leído.
MARKERS = ("\u00c3", "\u00c2", "\ufffd", "\u00ef\u00bf\u00bd")

ENDPOINTS = [
    "/api/v1/parametros-agua/?solo_activos=false",
    "/api/v1/referencias-agua/?solo_activos=false",
    "/api/v1/especies/?solo_activos=false",
    "/api/v1/etapas-productivas/?solo_activos=false",
    "/api/v1/referencias-produccion/?solo_activos=false",
    "/api/v1/referencias-biofloc/?solo_activos=false",
    "/api/v1/tipos-aplicacion-biofloc/?solo_activos=false",
    "/api/v1/categorias-inventario/?solo_activos=false",
    "/api/v1/unidades/",
    "/api/v1/tipos-movimiento-inventario/",
    "/api/v1/categorias-gasto/?solo_activos=false",
    "/api/v1/tipos-equipo/?solo_activos=false",
    "/api/v1/estados-equipo/?solo_activos=false",
    "/api/v1/tipos-mantenimiento/?solo_activos=false",
    "/api/v1/tipos-alarma/?solo_activos=false",
    "/api/v1/niveles-alarma/",
    "/api/v1/estados-alarma/",
    "/api/v1/estados-lote/?solo_activos=false",
    "/api/v1/estados-estanque/?solo_activos=false",
]


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" {detail}" if detail else ""))


def mojibake_hits(value: object, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        found = [marker for marker in MARKERS if marker in value]
        if found:
            hits.append(f"{path}={value!r}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            hits.extend(mojibake_hits(item, f"{path}[{i}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            hits.extend(mojibake_hits(item, f"{path}.{key}" if path else str(key)))
    return hits


def scan_sources() -> list[str]:
    hits: list[str] = []
    roots = [
        ROOT / "database",
        ROOT / "frontend" / "src",
        ROOT / "backend" / "app",
    ]
    skip_parts = {".pyc", "__pycache__", "node_modules", "dist"}
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            if path.suffix.lower() not in {".sql", ".py", ".ts", ".tsx", ".html", ".css", ".json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                hits.append(f"{path.relative_to(ROOT)} no es UTF-8: {exc}")
                continue
            for marker in MARKERS:
                if marker in text:
                    rel = path.relative_to(ROOT)
                    hits.append(f"{rel} contiene {marker!r}")
                    break
    return hits


def main() -> int:
    health = requests.get(f"{BASE}/health", timeout=20)
    check("GET /health 200", health.status_code == 200 and health.json().get("database") == "ok", health.text[:120])

    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute("SHOW server_encoding")
    server_enc = cur.fetchone()[0]
    cur.execute("SHOW client_encoding")
    client_enc = cur.fetchone()[0]
    cur.execute("SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()")
    db_enc = cur.fetchone()[0]
    check("PostgreSQL UTF8", server_enc == "UTF8" and client_enc == "UTF8" and db_enc == "UTF8", f"server={server_enc} client={client_enc} db={db_enc}")

    cur.execute(
        """
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = 'biofloc'
          AND t.table_type = 'BASE TABLE'
          AND c.data_type IN ('text', 'character varying', 'character')
          AND NOT (c.table_name = 'auditoria' AND c.column_name = 'detalle')
        """
    )
    db_hits: list[str] = []
    for table, column in cur.fetchall():
        try:
            cur.execute(
                f"SELECT COUNT(*) FROM biofloc.{table} "
                f"WHERE {column} IS NOT NULL AND ("
                f"{column} LIKE '%%' || chr(195) || '%%' OR "
                f"{column} LIKE '%%' || chr(194) || '%%')"
            )
            n = int(cur.fetchone()[0])
        except Exception as exc:
            conn.rollback()
            db_hits.append(f"{table}.{column} ERROR {exc}")
            continue
        if n:
            db_hits.append(f"{table}.{column}={n}")
    cur.close()
    conn.close()
    check("DB catálogos sin mojibake", not db_hits, str(db_hits[:12]))

    login = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": ADMIN_USER, "password": ADMIN_PASS},
        timeout=20,
    )
    check("login ADMIN", login.status_code == 200, str(login.status_code))
    if login.status_code != 200:
        print(f"\nRESULT {sum(1 for _, ok, _ in R if ok)}/{len(R)} OK")
        return 1
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    api_hits: list[str] = []
    oxigeno = False
    grado = False
    for ep in ENDPOINTS:
        r = requests.get(f"{BASE}{ep}", headers=headers, timeout=20)
        if r.status_code != 200:
            check(f"GET {ep}", False, str(r.status_code))
            continue
        ctype = r.headers.get("content-type", "")
        if "application/json" not in ctype:
            api_hits.append(f"{ep} content-type={ctype}")
        try:
            raw = r.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            api_hits.append(f"{ep} no UTF-8: {exc}")
            continue
        payload = r.json()
        hits = mojibake_hits(payload, ep)
        api_hits.extend(hits[:8])
        if ep.startswith("/api/v1/parametros-agua"):
            for fila in payload:
                if "Oxígeno" in str(fila.get("nombre") or ""):
                    oxigeno = True
                if fila.get("unidad") == "°C":
                    grado = True
    check("API catálogos UTF-8 sin mojibake", not api_hits, str(api_hits[:10]))
    check("Oxígeno disuelto en parámetros", oxigeno)
    check("unidad °C en parámetros", grado)

    fuente_hits = scan_sources()
    check("fuentes SQL/app/frontend UTF-8 sin mojibake", not fuente_hits, str(fuente_hits[:10]))

    leftover = 0 if not db_hits else len(db_hits)
    check("MOJIBAKE leftover", leftover == 0, str(leftover))

    ok = sum(1 for _, bien, _ in R if bien)
    print(f"\nRESULT {ok}/{len(R)} OK")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
