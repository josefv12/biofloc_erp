#!/usr/bin/env python3
"""FASE 10 — EQUIPOS + catálogos tipos/estados. Prefijo [TEST_EQUIPO]."""
import sys
import io
import requests
import psycopg2
from datetime import date
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}
ADMIN_USER, ADMIN_PASS = "admin@biofloc.com", "AdminBiofloc2026!"
TECNICO_USER, TECNICO_PASS = "tecnico_test@biofloc.com", "Tecnico1234!"
OPERARIO_USER, OPERARIO_PASS = "operario_test@biofloc.com", "Operario1234!"
DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp", user="postgres", password="admin")
PREF = "[TEST_EQUIPO]"
T = {"tipo_id": None, "estado_id": None, "equipo_ids": [], "tipo_seed_blower": None, "estado_seed_op": None}
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
    print(f"\n{PREF} INICIO suite test_equipos.py\n")
    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok", str(r.json()))
    tok_a, tok_t, tok_o = login(ADMIN_USER, ADMIN_PASS), login(TECNICO_USER, TECNICO_PASS), login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1
    r = requests.get(f"{BASE}/api/v1/equipos/")
    log(3, "GET equipos sin JWT -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_o))
    ok = r.status_code == 200 and len(r.json()) >= 5
    if ok:
        for t in r.json():
            if t["nombre"] == "BLOWER":
                T["tipo_seed_blower"] = t["id"]
    log(4, "GET tipos-equipo semilla >=5 OPERARIO", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_t))
    ok = r.status_code == 200 and len(r.json()) >= 4
    if ok:
        for e in r.json():
            if e["nombre"] == "OPERATIVO":
                T["estado_seed_op"] = e["id"]
    log(5, "GET estados-equipo semilla >=4 TECNICO", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.post(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a),
                      json={"nombre": f"{PREF} TIPO_X", "descripcion": "cat prueba", "activo": True})
    ok = r.status_code == 201
    if ok:
        T["tipo_id"] = r.json()["id"]
    log(6, "POST tipo-equipo ADMIN 201", ok, f"status={r.status_code} id={T['tipo_id']}")

    r = requests.post(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a), json={"nombre": f"{PREF} TIPO_X"})
    log(7, "POST tipo duplicado -> 409", r.status_code == 409, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_o), json={"nombre": f"{PREF} NO"})
    log(8, "POST tipo OPERARIO -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.put(f"{BASE}/api/v1/tipos-equipo/{T['tipo_id']}", headers=h(tok_t),
                     json={"descripcion": f"{PREF} actualizado"})
    log(9, "PUT tipo-equipo TECNICO 200", r.status_code == 200, f"status={r.status_code}")

    body = {
        "codigo": f"{PREF}-BLW-01",
        "nombre": f"{PREF} Blower prueba",
        "tipo_equipo_id": T["tipo_seed_blower"],
        "estado_id": T["estado_seed_op"],
        "marca": "TestMarca",
        "modelo": "TM-100",
        "numero_serie": "SN-001",
        "fecha_adquisicion": date.today().isoformat(),
        "valor_adquisicion": "1500000.50",
        "ubicacion": "Sala de sopladores",
        "observaciones": f"{PREF} obs",
        "activo": True,
    }
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json=body)
    ok = r.status_code == 201
    if ok:
        data = r.json()
        T["equipo_ids"].append(data["id"])
        ok = (data["codigo"] == f"{PREF}-BLW-01"
              and Decimal(str(data["valor_adquisicion"])) == Decimal("1500000.50")
              and data["tipo"]["nombre"] == "BLOWER"
              and data["estado"]["nombre"] == "OPERATIVO")
    log(10, "POST equipo válido ADMIN 201", ok, f"status={r.status_code} body={r.text[:220]}")

    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json=body)
    log(11, "POST equipo codigo UNIQUE -> 409", r.status_code == 409, f"status={r.status_code}")

    bad = {**body, "codigo": f"{PREF}-X", "tipo_equipo_id": 99999999}
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json=bad)
    log(12, "POST equipo tipo inexistente -> 404", r.status_code == 404, f"status={r.status_code}")

    bad = {**body, "codigo": f"{PREF}-Y", "tipo_equipo_id": T["tipo_seed_blower"], "estado_id": 99999999}
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json=bad)
    log(13, "POST equipo estado inexistente -> 404", r.status_code == 404, f"status={r.status_code}")

    bad = {**body, "codigo": f"{PREF}-Z", "valor_adquisicion": "-1.00", "estado_id": T["estado_seed_op"]}
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json=bad)
    log(14, "POST equipo valor_adquisicion < 0 -> 422", r.status_code == 422, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_o), json={**body, "codigo": f"{PREF}-OP"})
    log(15, "POST equipo OPERARIO -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/equipos/?codigo={PREF}", headers=h(tok_o))
    ok = r.status_code == 200 and len(r.json()) >= 1
    log(16, "GET equipos filtro codigo OPERARIO", ok, f"status={r.status_code} n={len(r.json()) if r.status_code==200 else '?'}")

    eid = T["equipo_ids"][0]
    r = requests.get(f"{BASE}/api/v1/equipos/{eid}", headers=h(tok_t))
    log(17, "GET equipo/{id} TECNICO 200", r.status_code == 200 and r.json()["id"] == eid, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/equipos/99999999", headers=h(tok_a))
    log(18, "GET equipo inexistente -> 404", r.status_code == 404, f"status={r.status_code}")

    r = requests.put(f"{BASE}/api/v1/equipos/{eid}", headers=h(tok_t), json={"activo": False, "ubicacion": f"{PREF} relocated"})
    ok = r.status_code == 200 and r.json()["activo"] is False
    log(19, "PUT equipo TECNICO 200 (activo/ubicacion)", ok, f"status={r.status_code}")

    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla IN ('equipos','tipos_equipo') AND detalle::text LIKE %s", (f"%{PREF}%",))
    n_aud = cur.fetchone()[0]
    cur.close(); conn.close()
    log(20, f"Auditoría equipos/tipos INSERT+UPDATE n={n_aud}>=3", n_aud >= 3, f"n={n_aud}")

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    ops_eq = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/equipos")}
    mal = [(p, m) for p, m in ops_eq.items() if "delete" in [x.lower() for x in m]]
    has_put = any("put" in [x.lower() for x in m] for m in ops_eq.values())
    log(21, "OpenAPI equipos: GET+POST+PUT, sin DELETE", len(mal) == 0 and has_put, f"ops={ops_eq}")

    try:
        conn = pg(); cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        if T["equipo_ids"]:
            cur.execute("DELETE FROM biofloc.equipos WHERE id = ANY(%s)", (T["equipo_ids"],))
        if T["tipo_id"]:
            cur.execute("DELETE FROM biofloc.tipos_equipo WHERE id = %s", (T["tipo_id"],))
        conn.commit()
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.tipos_equipo WHERE nombre LIKE %s", (f"%{PREF}%",))
        nt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.close(); conn.close()
        log(22, f"Limpieza 0 residuales eq={ne} tipo={nt} aud={na}", ne == 0 and nt == 0 and na == 0)
    except Exception as e:
        log(22, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
