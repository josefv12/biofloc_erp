#!/usr/bin/env python3
"""FASE 10 — MANTENIMIENTOS (inmutables) + catálogo tipos. Prefijo [TEST_MANT]."""
import sys
import io
import requests
import psycopg2
from datetime import date, timedelta
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}
ADMIN_USER, ADMIN_PASS = "admin@biofloc.com", "AdminBiofloc2026!"
TECNICO_USER, TECNICO_PASS = "tecnico_test@biofloc.com", "Tecnico1234!"
OPERARIO_USER, OPERARIO_PASS = "operario_test@biofloc.com", "Operario1234!"
DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp", user="postgres", password="admin")
PREF = "[TEST_MANT]"
T = {"equipo_id": None, "tipo_seed": None, "tipo_extra": None, "mant_ids": []}
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
    print(f"\n{PREF} INICIO suite test_mantenimientos.py\n")
    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("database") == "ok")
    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1
    r = requests.get(f"{BASE}/api/v1/mantenimientos/")
    log(3, "GET mantenimientos sin JWT -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/tipos-mantenimiento/", headers=h(tok_o))
    ok = r.status_code == 200 and len(r.json()) >= 2
    if ok:
        for t in r.json():
            if t["nombre"] == "PREVENTIVO":
                T["tipo_seed"] = t["id"]
    log(4, "GET tipos-mantenimiento semilla OPERARIO", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.post(f"{BASE}/api/v1/tipos-mantenimiento/", headers=h(tok_o), json={"nombre": f"{PREF} NO"})
    log(5, "POST tipo-mant OPERARIO -> 403", r.status_code == 403)

    r = requests.post(f"{BASE}/api/v1/tipos-mantenimiento/", headers=h(tok_a),
                      json={"nombre": f"{PREF} EXTRA", "activo": True})
    ok = r.status_code == 201
    if ok:
        T["tipo_extra"] = r.json()["id"]
    log(6, "POST tipo-mant ADMIN 201", ok, f"id={T['tipo_extra']}")

    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next(t["id"] for t in r.json() if t["nombre"] == "BOMBA")
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est = next(e["id"] for e in r.json() if e["nombre"] == "OPERATIVO")
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-EQ-01", "nombre": f"{PREF} Bomba", "tipo_equipo_id": tipo_eq, "estado_id": est,
    })
    ok = r.status_code == 201
    if ok:
        T["equipo_id"] = r.json()["id"]
    log(7, "Semilla equipo para mantenimientos", ok, f"equipo_id={T['equipo_id']}")

    body = {
        "equipo_id": T["equipo_id"],
        "tipo_mantenimiento_id": T["tipo_seed"],
        "fecha": date.today().isoformat(),
        "descripcion": f"{PREF} Cambio de aceite",
        "costo": "250000.00",
        "proveedor": f"{PREF} Taller",
        "observaciones": f"{PREF} obs",
    }
    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json=body)
    ok = r.status_code == 201
    if ok:
        T["mant_ids"].append(r.json()["id"])
        ok = Decimal(str(r.json()["costo"])) == Decimal("250000.00")
    log(8, "POST mantenimiento válido ADMIN 201", ok, f"status={r.status_code} body={r.text[:220]}")

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json={**body, "equipo_id": 99999999})
    log(9, "POST mant equipo inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a),
                      json={**body, "tipo_mantenimiento_id": 99999999})
    log(10, "POST mant tipo inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json={**body, "costo": "-1.00"})
    log(11, "POST mant costo < 0 -> 422", r.status_code == 422)

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json={**body, "descripcion": "   "})
    log(12, "POST mant descripcion vacía -> 422", r.status_code == 422)

    body2 = {**body, "fecha": (date.today() - timedelta(days=2)).isoformat(),
             "descripcion": f"{PREF} Correctivo", "tipo_mantenimiento_id": T["tipo_extra"], "costo": "0.00"}
    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_o), json=body2)
    ok = r.status_code == 201
    if ok:
        T["mant_ids"].append(r.json()["id"])
        ok = Decimal(str(r.json()["costo"])) == Decimal("0.00")
    log(13, "POST mant OPERARIO 201 costo=0", ok, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/mantenimientos/?equipo_id={T['equipo_id']}", headers=h(tok_t))
    ok = r.status_code == 200 and len(r.json()) >= 2
    log(14, "GET lista filtro equipo_id", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    hoy = date.today().isoformat()
    r = requests.get(f"{BASE}/api/v1/mantenimientos/?fecha_desde={hoy}", headers=h(tok_a))
    ok = r.status_code == 200 and all(m["fecha"] >= hoy for m in r.json() if PREF in m["descripcion"])
    log(15, "GET lista filtro fecha_desde", ok)

    mid = T["mant_ids"][0]
    r = requests.get(f"{BASE}/api/v1/mantenimientos/{mid}", headers=h(tok_o))
    log(16, "GET mant/{id} 200", r.status_code == 200 and r.json()["id"] == mid)

    r = requests.get(f"{BASE}/api/v1/mantenimientos/99999999", headers=h(tok_a))
    log(17, "GET mant inexistente -> 404", r.status_code == 404)

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    ops = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/mantenimientos")}
    mal = [(p, m) for p, m in ops.items() if any(x in [i.lower() for i in m] for x in ["put", "delete", "patch"])]
    log(18, "OpenAPI mantenimientos: SOLO GET+POST", len(mal) == 0 and len(ops) >= 2, f"ops={ops}")

    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla='mantenimientos' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n = cur.fetchone()[0]
    cur.close(); conn.close()
    log(19, f"Auditoría mantenimientos INSERT n={n}>=2", n >= 2)

    try:
        conn = pg(); cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        if T["mant_ids"]:
            cur.execute("DELETE FROM biofloc.mantenimientos WHERE id = ANY(%s)", (T["mant_ids"],))
        if T["equipo_id"]:
            cur.execute("DELETE FROM biofloc.equipos WHERE id = %s", (T["equipo_id"],))
        if T["tipo_extra"]:
            cur.execute("DELETE FROM biofloc.tipos_mantenimiento WHERE id = %s", (T["tipo_extra"],))
        conn.commit()
        cur.execute("SELECT count(*) FROM biofloc.mantenimientos m JOIN biofloc.equipos e ON e.id=m.equipo_id WHERE e.codigo LIKE %s", (f"%{PREF}%",))
        # after delete equipos, check by descripcion
        cur.execute("SELECT count(*) FROM biofloc.mantenimientos WHERE descripcion LIKE %s", (f"%{PREF}%",))
        nm = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.close(); conn.close()
        log(20, f"Limpieza 0 residuales m={nm} e={ne} a={na}", nm == 0 and ne == 0 and na == 0)
    except Exception as e:
        log(20, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
