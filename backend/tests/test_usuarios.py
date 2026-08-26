#!/usr/bin/env python3
"""Gestión de usuarios: solo ADMINISTRADOR.

Prefijo [TEST_USUARIOS]. leftover = 0 al terminar.
No toca el administrador real más allá de intentar (y rechazar) desactivarlo.
"""
from __future__ import annotations

import io
import sys
import uuid

import psycopg2
import requests

from env_tests import (
    ADMIN_PASS,
    ADMIN_USER,
    DB_CONF,
    OPERARIO_PASS,
    OPERARIO_USER,
    TECNICO_PASS,
    TECNICO_USER,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_USUARIOS]"
SUF = uuid.uuid4().hex[:8]
CORREO = f"test.usuarios.{SUF}@biofloc.test"
R: list[tuple[str, bool, str]] = []
IDS: dict[str, int | None] = {"usuario": None}


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" {detail}" if detail else ""))


def login(correo: str, password: str) -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": correo, "password": password},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def db():
    return psycopg2.connect(**DB_CONF)


def leftover() -> int:
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM biofloc.usuarios WHERE correo LIKE %s OR nombre LIKE %s",
        ("test.usuarios.%@biofloc.test", f"{PREF}%"),
    )
    n = int(cur.fetchone()[0])
    cur.execute(
        "SELECT COUNT(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s",
        (f"%{PREF}%",),
    )
    n += int(cur.fetchone()[0])
    cur.execute(
        "SELECT COUNT(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s",
        (f"%{CORREO}%",),
    )
    n += int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def cleanup() -> int:
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM biofloc.usuarios WHERE correo LIKE %s OR nombre LIKE %s",
        ("test.usuarios.%@biofloc.test", f"{PREF}%"),
    )
    ids = [row[0] for row in cur.fetchall()]
    if ids:
        cur.execute(
            "DELETE FROM biofloc.auditoria WHERE tabla='usuarios' AND registro_id = ANY(%s)",
            (ids,),
        )
        cur.execute("DELETE FROM biofloc.usuarios WHERE id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{CORREO}%",))
    conn.commit()
    cur.close()
    conn.close()
    return leftover()


def main() -> int:
    try:
        requests.get(f"{BASE}/health", timeout=3).raise_for_status()
    except Exception:
        print(f"El servidor no responde en {BASE}")
        return 1

    cleanup()
    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)

    r = requests.get(f"{BASE}/api/v1/usuarios/", headers=H(tok_a), timeout=20)
    check("ADMIN GET usuarios 200", r.status_code == 200, str(r.status_code))
    lista = r.json() if r.status_code == 200 else []
    check("ADMIN lista no vacía", isinstance(lista, list) and len(lista) >= 1, str(len(lista) if isinstance(lista, list) else lista))
    check(
        "respuesta sin password_hash",
        all("password_hash" not in row and "password" not in row for row in lista) if lista else False,
    )

    r = requests.get(f"{BASE}/api/v1/usuarios/", headers=H(tok_t), timeout=20)
    check("TECNICO GET usuarios 403", r.status_code == 403, str(r.status_code))
    r = requests.get(f"{BASE}/api/v1/usuarios/", headers=H(tok_o), timeout=20)
    check("OPERARIO GET usuarios 403", r.status_code == 403, str(r.status_code))

    r = requests.get(f"{BASE}/api/v1/roles/", headers=H(tok_a), timeout=20)
    check("ADMIN GET roles 200", r.status_code == 200, str(r.status_code))
    roles = r.json() if r.status_code == 200 else []
    nombres = {row["nombre"]: row["id"] for row in roles}
    check("roles reales presentes", {"ADMINISTRADOR", "TECNICO", "OPERARIO"} <= set(nombres), str(sorted(nombres)))
    r = requests.get(f"{BASE}/api/v1/roles/", headers=H(tok_t), timeout=20)
    check("TECNICO GET roles 403", r.status_code == 403, str(r.status_code))

    body = {
        "nombre": f"{PREF} Técnico temporal",
        "correo": CORREO,
        "password": "Temporal.8",
        "rol_id": nombres.get("TECNICO"),
        "activo": True,
    }
    r = requests.post(f"{BASE}/api/v1/usuarios/", headers=H(tok_t), json=body, timeout=20)
    check("TECNICO POST usuario 403", r.status_code == 403, str(r.status_code))

    r = requests.post(f"{BASE}/api/v1/usuarios/", headers=H(tok_a), json=body, timeout=20)
    check("ADMIN POST usuario 201", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    creado = r.json() if r.status_code == 201 else {}
    IDS["usuario"] = creado.get("id")
    check("POST sin hash", "password_hash" not in creado and "password" not in creado, str(creado.keys()))
    check("rol TECNICO", creado.get("rol") == "TECNICO", str(creado.get("rol")))

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM biofloc.usuarios WHERE id=%s", (IDS["usuario"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    hash_val = row[0] if row else ""
    check("hash bcrypt almacenado", isinstance(hash_val, str) and hash_val.startswith("$2") and len(hash_val) > 20, hash_val[:12] if hash_val else "NONE")
    check("password plano ausente en BD", "Temporal.8" not in str(hash_val), "")

    r = requests.put(
        f"{BASE}/api/v1/usuarios/{IDS['usuario']}",
        headers=H(tok_a),
        json={"nombre": f"{PREF} Técnico editado"},
        timeout=20,
    )
    check("ADMIN PUT nombre 200", r.status_code == 200 and r.json().get("nombre") == f"{PREF} Técnico editado", str(r.status_code))

    r = requests.put(
        f"{BASE}/api/v1/usuarios/{IDS['usuario']}",
        headers=H(tok_t),
        json={"rol_id": nombres.get("ADMINISTRADOR")},
        timeout=20,
    )
    check("TECNICO PUT rol 403", r.status_code == 403, str(r.status_code))

    r = requests.put(
        f"{BASE}/api/v1/usuarios/{IDS['usuario']}",
        headers=H(tok_a),
        json={"rol_id": nombres.get("OPERARIO")},
        timeout=20,
    )
    check("ADMIN cambia rol a OPERARIO", r.status_code == 200 and r.json().get("rol") == "OPERARIO", str(r.status_code))

    r = requests.put(
        f"{BASE}/api/v1/usuarios/{IDS['usuario']}",
        headers=H(tok_a),
        json={"activo": False},
        timeout=20,
    )
    check("ADMIN desactiva usuario", r.status_code == 200 and r.json().get("activo") is False, str(r.status_code))

    r = requests.put(
        f"{BASE}/api/v1/usuarios/{IDS['usuario']}",
        headers=H(tok_a),
        json={"activo": True, "rol_id": nombres.get("TECNICO")},
        timeout=20,
    )
    check("ADMIN reactiva y rol TECNICO", r.status_code == 200 and r.json().get("activo") is True, str(r.status_code))

    me = requests.get(f"{BASE}/api/v1/auth/me", headers=H(tok_a), timeout=20).json()
    r = requests.put(
        f"{BASE}/api/v1/usuarios/{me['id']}",
        headers=H(tok_a),
        json={"activo": False},
        timeout=20,
    )
    check("último ADMIN no se desactiva 409", r.status_code == 409, f"{r.status_code} {r.text[:180]}")
    r = requests.put(
        f"{BASE}/api/v1/usuarios/{me['id']}",
        headers=H(tok_a),
        json={"rol_id": nombres.get("TECNICO")},
        timeout=20,
    )
    check("último ADMIN no cambia de rol 409", r.status_code == 409, f"{r.status_code} {r.text[:180]}")

    r = requests.post(
        f"{BASE}/api/v1/usuarios/",
        headers=H(tok_a),
        json={**body, "correo": CORREO, "password": "corta"},
        timeout=20,
    )
    check("password corta 422", r.status_code == 422, str(r.status_code))

    n = cleanup()
    check("LEFTOVER usuarios = 0", n == 0, str(n))

    passed = sum(1 for _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2


if __name__ == "__main__":
    raise SystemExit(main())
