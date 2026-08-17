#!/usr/bin/env python3
"""FASE 10 — FALLAS. Prefijo [TEST_FALLA]. PUT limitado a solución/impacto/costo/descripcion."""
import sys
import io
import requests
import psycopg2
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}
PREF = "[TEST_FALLA]"
T = {"equipo_id": None, "falla_ids": []}
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

def h(tok):
    return {**HEADERS_JSON, "Authorization": f"Bearer {tok}"}

def pg():
    return psycopg2.connect(**DB_CONF)

def main():
    print(f"\n{PREF} INICIO suite test_fallas.py\n")
    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("database") == "ok")
    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1
    r = requests.get(f"{BASE}/api/v1/fallas/")
    log(3, "GET fallas sin JWT -> 403", r.status_code == 403)

    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next(t["id"] for t in r.json() if t["nombre"] == "BLOWER")
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est = next(e["id"] for e in r.json() if e["nombre"] == "OPERATIVO")
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-EQ-01", "nombre": f"{PREF} Blower", "tipo_equipo_id": tipo_eq, "estado_id": est,
    })
    ok = r.status_code == 201
    if ok:
        T["equipo_id"] = r.json()["id"]
    log(4, "Semilla equipo para fallas", ok, f"equipo_id={T['equipo_id']}")

    now = datetime.now(timezone.utc).isoformat()
    body = {
        "equipo_id": T["equipo_id"],
        "fecha_hora": now,
        "descripcion": f"{PREF} Vibración anormal",
        "impacto": "Aireación reducida",
        "costo": "0.00",
    }
    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json=body)
    ok = r.status_code == 201
    if ok:
        T["falla_ids"].append(r.json()["id"])
        ok = r.json()["solucion"] is None and Decimal(str(r.json()["costo"])) == Decimal("0.00")
    log(5, "POST falla válida sin solución ADMIN 201", ok, f"status={r.status_code} body={r.text[:240]}")

    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json={**body, "equipo_id": 99999999})
    log(6, "POST falla equipo inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json={**body, "costo": "-10.00"})
    log(7, "POST falla costo < 0 -> 422", r.status_code == 422)

    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json={**body, "descripcion": "  "})
    log(8, "POST falla descripcion vacía -> 422", r.status_code == 422)

    body2 = {
        "equipo_id": T["equipo_id"],
        "fecha_hora": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "descripcion": f"{PREF} Ruido",
        "costo": "50000.00",
    }
    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_o), json=body2)
    ok = r.status_code == 201
    if ok:
        T["falla_ids"].append(r.json()["id"])
    log(9, "POST falla OPERARIO 201", ok, f"status={r.status_code}")

    fid = T["falla_ids"][0]
    r = requests.put(f"{BASE}/api/v1/fallas/{fid}", headers=h(tok_t), json={
        "solucion": f"{PREF} Reajuste de anclajes",
        "costo": "80000.00",
        "impacto": "Temporal",
    })
    ok = r.status_code == 200 and r.json()["solucion"].startswith(PREF) and Decimal(str(r.json()["costo"])) == Decimal("80000.00")
    log(10, "PUT falla solución+costo TECNICO 200", ok, f"status={r.status_code} body={r.text[:240]}")

    r = requests.get(f"{BASE}/api/v1/fallas/?equipo_id={T['equipo_id']}", headers=h(tok_o))
    ok = r.status_code == 200 and len(r.json()) >= 2
    log(11, "GET fallas filtro equipo_id", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/fallas/{fid}", headers=h(tok_a))
    log(12, "GET falla/{id} 200", r.status_code == 200 and r.json()["id"] == fid)

    r = requests.get(f"{BASE}/api/v1/fallas/99999999", headers=h(tok_a))
    log(13, "GET falla inexistente -> 404", r.status_code == 404)

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    ops = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/fallas")}
    has_put = any("put" in [x.lower() for x in m] for m in ops.values())
    has_del = any("delete" in [x.lower() for x in m] for m in ops.values())
    log(14, "OpenAPI fallas: GET+POST+PUT, sin DELETE", has_put and not has_del, f"ops={ops}")

    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla='fallas' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n = cur.fetchone()[0]
    cur.close(); conn.close()
    log(15, f"Auditoría fallas INSERT+UPDATE n={n}>=3", n >= 3)

    try:
        conn = pg(); cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        if T["falla_ids"]:
            cur.execute("DELETE FROM biofloc.fallas WHERE id = ANY(%s)", (T["falla_ids"],))
        if T["equipo_id"]:
            cur.execute("DELETE FROM biofloc.equipos WHERE id = %s", (T["equipo_id"],))
        conn.commit()
        cur.execute("SELECT count(*) FROM biofloc.fallas WHERE descripcion LIKE %s", (f"%{PREF}%",))
        nf = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.close(); conn.close()
        log(16, f"Limpieza 0 residuales f={nf} e={ne} a={na}", nf == 0 and ne == 0 and na == 0)
    except Exception as e:
        log(16, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
