#!/usr/bin/env python3
"""FASE 10 — EVENTOS DE ENERGÍA. Prefijo [TEST_ENERGIA].

No genera filas en alarmas (sistema general = fase posterior).
No hay estanque_id en el DDL.
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}
PREF = "[TEST_ENERGIA]"
T = {"equipo_id": None, "evento_ids": []}
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
    print(f"\n{PREF} INICIO suite test_eventos_energia.py\n")
    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("database") == "ok")
    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1
    r = requests.get(f"{BASE}/api/v1/eventos-energia/")
    log(3, "GET eventos-energia sin JWT -> 403", r.status_code == 403)

    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next(t["id"] for t in r.json() if t["nombre"] == "PLANTA_ELECTRICA")
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est = next(e["id"] for e in r.json() if e["nombre"] == "OPERATIVO")
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-GEN-01", "nombre": f"{PREF} Planta", "tipo_equipo_id": tipo_eq, "estado_id": est,
    })
    ok = r.status_code == 201
    if ok:
        T["equipo_id"] = r.json()["id"]
    log(4, "Semilla planta eléctrica de respaldo", ok, f"equipo_id={T['equipo_id']}")

    inicio = datetime.now(timezone.utc)
    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": inicio.isoformat(),
        "tipo": "CORTE",
        "observaciones": f"{PREF} corte abierto",
    })
    ok = r.status_code == 201
    if ok:
        T["evento_ids"].append(r.json()["id"])
        ok = r.json()["fecha_hora_fin"] is None and r.json()["tipo"] == "CORTE"
    log(5, "POST evento abierto (sin fin) 201", ok, f"status={r.status_code} body={r.text[:240]}")

    ini = datetime.now(timezone.utc) - timedelta(minutes=45)
    fin = datetime.now(timezone.utc)
    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": ini.isoformat(),
        "fecha_hora_fin": fin.isoformat(),
        "tipo": "CORTE",
        "respaldo_activado": True,
        "equipo_respaldo_id": T["equipo_id"],
        "observaciones": f"{PREF} corte cerrado",
    })
    ok = r.status_code == 201
    dur = None
    if ok:
        T["evento_ids"].append(r.json()["id"])
        dur = r.json()["duracion_minutos"]
        ok = dur is not None and dur >= 40
    log(6, "POST evento cerrado: duración server-side + respaldo", ok, f"duracion={dur} status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": inicio.isoformat(),
        "respaldo_activado": True,
        "observaciones": f"{PREF} sin equipo",
    })
    log(7, "POST respaldo=true sin equipo -> 422", r.status_code == 422, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": inicio.isoformat(),
        "respaldo_activado": True,
        "equipo_respaldo_id": 99999999,
        "observaciones": f"{PREF} eq falso",
    })
    log(8, "POST respaldo equipo inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": inicio.isoformat(),
        "fecha_hora_fin": (inicio - timedelta(hours=1)).isoformat(),
        "observaciones": f"{PREF} fin<inicio",
    })
    log(9, "POST fecha_hora_fin < inicio -> 422", r.status_code == 422)

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_o), json={
        "fecha_hora_inicio": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "tipo": "FLUCTUACION",
        "observaciones": f"{PREF} operario",
    })
    ok = r.status_code == 201
    if ok:
        T["evento_ids"].append(r.json()["id"])
    log(10, "POST evento OPERARIO 201", ok, f"status={r.status_code}")

    abierto_id = T["evento_ids"][0]
    fin_cierre = datetime.now(timezone.utc)
    r = requests.put(f"{BASE}/api/v1/eventos-energia/{abierto_id}", headers=h(tok_t), json={
        "fecha_hora_fin": fin_cierre.isoformat(),
        "observaciones": f"{PREF} cerrado por PUT",
    })
    ok = r.status_code == 200 and r.json()["fecha_hora_fin"] is not None and r.json()["duracion_minutos"] is not None
    log(11, "PUT cierra evento y calcula duración", ok, f"status={r.status_code} dur={r.json().get('duracion_minutos') if r.status_code==200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/eventos-energia/?tipo=CORTE", headers=h(tok_a))
    ok = r.status_code == 200 and len(r.json()) >= 1
    log(12, "GET lista filtro tipo=CORTE", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/eventos-energia/?equipo_respaldo_id={T['equipo_id']}", headers=h(tok_t))
    ok = r.status_code == 200 and len(r.json()) >= 1
    log(13, "GET lista filtro equipo_respaldo_id", ok)

    r = requests.get(f"{BASE}/api/v1/eventos-energia/{abierto_id}", headers=h(tok_o))
    log(14, "GET evento/{id} 200", r.status_code == 200 and r.json()["id"] == abierto_id)

    r = requests.get(f"{BASE}/api/v1/eventos-energia/99999999", headers=h(tok_a))
    log(15, "GET evento inexistente -> 404", r.status_code == 404)

    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.alarmas WHERE evento_energia_id = ANY(%s)", (T["evento_ids"] or [0],))
    n_al = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla='eventos_energia' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n_au = cur.fetchone()[0]
    cur.close(); conn.close()
    log(16, "0 alarmas generadas desde eventos de energía", n_al == 0, f"n_alarmas={n_al}")
    log(17, f"Auditoría eventos_energia n={n_au}>=4", n_au >= 4)

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    ops = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/eventos-energia")}
    has_del = any("delete" in [x.lower() for x in m] for m in ops.values())
    log(18, "OpenAPI eventos-energia: GET+POST+PUT, sin DELETE", (not has_del) and len(ops) >= 2, f"ops={ops}")

    try:
        conn = pg(); cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        if T["evento_ids"]:
            cur.execute("DELETE FROM biofloc.eventos_energia WHERE id = ANY(%s)", (T["evento_ids"],))
        if T["equipo_id"]:
            cur.execute("DELETE FROM biofloc.equipos WHERE id = %s", (T["equipo_id"],))
        conn.commit()
        cur.execute("SELECT count(*) FROM biofloc.eventos_energia WHERE observaciones LIKE %s", (f"%{PREF}%",))
        nv = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.close(); conn.close()
        log(19, f"Limpieza 0 residuales ev={nv} eq={ne} a={na}", nv == 0 and ne == 0 and na == 0)
    except Exception as e:
        log(19, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
