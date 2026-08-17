#!/usr/bin/env python3
"""FASE 11 — SISTEMA GENERAL DE ALARMAS. Prefijo [TEST_ALARMA_GENERAL].

No confundir con [TEST_ALARMA] de /api/v1/alertas/stock-bajo.
Estados reales DDL: PENDIENTE, ATENDIDA, CERRADA.
No hay automatización falla→alarma ni triggers.
"""
import sys
import io
import hashlib
import pathlib
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
PREF = "[TEST_ALARMA_GENERAL]"
DDL_SHA = "b35db89dc83fad95c10fc88fece04e031e680b3b921b12b5a584bfb4047bd2e3"
T = {
    "tipo_extra_id": None,
    "nivel_extra_id": None,
    "estado_extra_id": None,
    "tipo_seed": {},
    "nivel_seed": {},
    "estado_seed": {},
    "lote_id": None,
    "equipo_id": None,
    "evento_id": None,
    "alarma_ids": [],
    "admin_id": None,
    "operario_id": None,
}
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

def pre_cleanup():
    conn = pg()
    cur = conn.cursor()
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.alarmas WHERE titulo LIKE %s OR mensaje LIKE %s OR observaciones LIKE %s",
                (f"%{PREF}%", f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.eventos_energia WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.equipos WHERE codigo LIKE %s OR nombre LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.tipos_alarma WHERE nombre = %s", ("TEST_ALARMA_GENERAL_TIPO",))
    cur.execute("DELETE FROM biofloc.niveles_alarma WHERE nombre = %s", ("TAG_NIVEL",))
    cur.execute("DELETE FROM biofloc.estados_alarma WHERE nombre = %s", ("TAG_ESTADO",))
    cur.execute("DELETE FROM biofloc.auditoria WHERE tabla IN ('tipos_alarma','niveles_alarma','estados_alarma') AND detalle::text LIKE %s",
                ("%TEST_ALARMA_GENERAL_TIPO%",))
    cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='niveles_alarma' AND detalle::text LIKE %s", ("%TAG_NIVEL%",))
    cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estados_alarma' AND detalle::text LIKE %s", ("%TAG_ESTADO%",))
    conn.commit()
    cur.close()
    conn.close()

def main():
    print(f"\n{PREF} INICIO suite test_alarmas.py\n")
    pre_cleanup()

    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok", str(r.json()))

    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1

    r = requests.get(f"{BASE}/api/v1/alarmas/")
    log(3, "GET alarmas sin JWT -> 403", r.status_code == 403, f"status={r.status_code}")

    conn = pg()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.usuarios WHERE correo=%s", (ADMIN_USER,))
    T["admin_id"] = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.usuarios WHERE correo=%s", (OPERARIO_USER,))
    T["operario_id"] = cur.fetchone()[0]
    cur.close()
    conn.close()

    r = requests.get(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_o))
    nombres_tipo = [t["nombre"] for t in r.json()] if r.status_code == 200 else []
    esperados_tipo = {"CORTE_ELECTRICO", "PARAMETRO_AGUA", "NIVEL_BIOFLOC", "EQUIPO", "INVENTARIO_BAJO"}
    ok = r.status_code == 200 and esperados_tipo.issubset(set(nombres_tipo))
    if r.status_code == 200:
        T["tipo_seed"] = {t["nombre"]: t["id"] for t in r.json()}
    log(4, "GET tipos-alarma semilla 5 nombres reales", ok, f"nombres={nombres_tipo}")

    r = requests.get(f"{BASE}/api/v1/niveles-alarma/", headers=h(tok_t))
    niveles = r.json() if r.status_code == 200 else []
    mapa_n = {n["nombre"]: n["prioridad"] for n in niveles}
    ok = r.status_code == 200 and mapa_n.get("BAJA") == 1 and mapa_n.get("MEDIA") == 2 and mapa_n.get("ALTA") == 3 and mapa_n.get("CRITICA") == 4
    if r.status_code == 200:
        T["nivel_seed"] = {n["nombre"]: n["id"] for n in niveles}
    log(5, "GET niveles-alarma BAJA/MEDIA/ALTA/CRITICA", ok, f"mapa={mapa_n}")

    r = requests.get(f"{BASE}/api/v1/estados-alarma/", headers=h(tok_a))
    estados = r.json() if r.status_code == 200 else []
    nombres_est = [e["nombre"] for e in estados]
    ok = r.status_code == 200 and set(nombres_est) >= {"PENDIENTE", "ATENDIDA", "CERRADA"}
    ok = ok and "RESUELTA" not in nombres_est and "CANCELADA" not in nombres_est
    if r.status_code == 200:
        T["estado_seed"] = {e["nombre"]: e["id"] for e in estados}
    log(6, "GET estados-alarma PENDIENTE/ATENDIDA/CERRADA (nomenclatura real)", ok, f"nombres={nombres_est}")

    r = requests.post(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_a), json={
        "nombre": "TEST_ALARMA_GENERAL_TIPO", "descripcion": f"{PREF} tipo extra", "activo": True,
    })
    ok = r.status_code == 201
    if ok:
        T["tipo_extra_id"] = r.json()["id"]
    log(7, "POST tipo-alarma ADMIN 201", ok, f"status={r.status_code} id={T['tipo_extra_id']}")

    r = requests.post(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_a), json={"nombre": "TEST_ALARMA_GENERAL_TIPO"})
    log(8, "POST tipo duplicado -> 409", r.status_code == 409, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_o), json={"nombre": "TAG_NO"})
    log(9, "POST tipo OPERARIO -> 403", r.status_code == 403, f"status={r.status_code}")

    r = requests.put(f"{BASE}/api/v1/tipos-alarma/{T['tipo_extra_id']}", headers=h(tok_t),
                     json={"descripcion": f"{PREF} tipo actualizado"})
    log(10, "PUT tipo-alarma TECNICO 200", r.status_code == 200, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/niveles-alarma/", headers=h(tok_a), json={"nombre": "TAG_CERO", "prioridad": 0})
    log(11, "POST nivel prioridad=0 -> 422", r.status_code == 422, f"status={r.status_code} body={r.text[:160]}")

    r = requests.post(f"{BASE}/api/v1/niveles-alarma/", headers=h(tok_a), json={"nombre": "TAG_NIVEL", "prioridad": 5})
    ok = r.status_code == 201 and r.json().get("prioridad") == 5
    if r.status_code == 201:
        T["nivel_extra_id"] = r.json()["id"]
    log(12, "POST nivel extra prioridad=5 ADMIN 201", ok, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/estados-alarma/", headers=h(tok_a), json={
        "nombre": "TAG_ESTADO", "descripcion": f"{PREF} estado extra",
    })
    ok = r.status_code == 201
    if ok:
        T["estado_extra_id"] = r.json()["id"]
    log(13, "POST estado extra ADMIN 201", ok, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/estados-alarma/", headers=h(tok_o), json={"nombre": "TAG_NO_EST"})
    log(14, "POST estado OPERARIO -> 403", r.status_code == 403)

    r = requests.get(f"{BASE}/api/v1/lotes/", headers=h(tok_a))
    ok = r.status_code == 200 and len(r.json()) >= 1
    if ok:
        T["lote_id"] = r.json()[0]["id"]
    log(15, f"Resuelto lote_id={T['lote_id']}", ok)

    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next((t["id"] for t in r.json() if t["nombre"] == "BLOWER"), r.json()[0]["id"] if r.status_code == 200 else None)
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est_eq = next((e["id"] for e in r.json() if e["nombre"] == "OPERATIVO"), r.json()[0]["id"] if r.status_code == 200 else None)
    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-EQ-01", "nombre": f"{PREF} Equipo", "tipo_equipo_id": tipo_eq, "estado_id": est_eq,
    })
    ok = r.status_code == 201
    if ok:
        T["equipo_id"] = r.json()["id"]
    log(16, "Semilla equipo para FK equipo_id", ok, f"equipo_id={T['equipo_id']} status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": datetime.now(timezone.utc).isoformat(),
        "tipo": "CORTE",
        "observaciones": f"{PREF} corte para FK",
    })
    ok = r.status_code == 201
    if ok:
        T["evento_id"] = r.json()["id"]
    log(17, "Semilla evento_energia para FK", ok, f"evento_id={T['evento_id']}")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["EQUIPO"],
        "nivel_alarma_id": T["nivel_seed"]["ALTA"],
        "titulo": f"{PREF} blower",
        "mensaje": f"{PREF} falla reportada manualmente",
        "equipo_id": T["equipo_id"],
    })
    ok = r.status_code == 201
    data = r.json() if ok else {}
    if ok:
        T["alarma_ids"].append(data["id"])
        ok = (data["estado"]["nombre"] == "PENDIENTE"
              and data["tipo"]["nombre"] == "EQUIPO"
              and data["nivel"]["nombre"] == "ALTA"
              and data["atendida_por"] is None
              and data["fecha_atencion"] is None
              and data["equipo_id"] == T["equipo_id"])
    log(18, "POST alarma EQUIPO PENDIENTE default 201", ok, f"status={r.status_code} body={r.text[:280]}")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_t), json={
        "tipo_alarma_id": T["tipo_seed"]["PARAMETRO_AGUA"],
        "nivel_alarma_id": T["nivel_seed"]["CRITICA"],
        "lote_id": T["lote_id"],
        "titulo": f"{PREF} pH",
        "mensaje": f"{PREF} parámetro agua asociado a lote (sin FK a medición)",
    })
    ok = r.status_code == 201
    if ok:
        T["alarma_ids"].append(r.json()["id"])
        ok = r.json()["lote_id"] == T["lote_id"] and r.json()["tipo"]["nombre"] == "PARAMETRO_AGUA"
    log(19, "POST alarma PARAMETRO_AGUA + lote_id", ok, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["CORTE_ELECTRICO"],
        "nivel_alarma_id": T["nivel_seed"]["MEDIA"],
        "evento_energia_id": T["evento_id"],
        "titulo": f"{PREF} corte",
        "mensaje": f"{PREF} vinculado a evento_energia (manual, no trigger)",
    })
    ok = r.status_code == 201
    if ok:
        T["alarma_ids"].append(r.json()["id"])
        ok = r.json()["evento_energia_id"] == T["evento_id"]
    log(20, "POST alarma CORTE_ELECTRICO + evento_energia_id (sin automatizar)", ok)

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["INVENTARIO_BAJO"],
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "titulo": f"{PREF} stock",
        "mensaje": f"{PREF} representación genérica; no reemplaza /alertas/stock-bajo",
    })
    ok = r.status_code == 201
    if ok:
        T["alarma_ids"].append(r.json()["id"])
    log(21, "POST alarma INVENTARIO_BAJO genérica (sin producto_id en DDL)", ok, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": 99999999,
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "titulo": f"{PREF} bad tipo",
        "mensaje": f"{PREF} fk",
    })
    log(22, "POST tipo_alarma_id inexistente -> 404", r.status_code == 404, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["EQUIPO"],
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "lote_id": 99999999,
        "titulo": f"{PREF} bad lote",
        "mensaje": f"{PREF} fk",
    })
    log(23, "POST lote_id inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["EQUIPO"],
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "equipo_id": 99999999,
        "titulo": f"{PREF} bad eq",
        "mensaje": f"{PREF} fk",
    })
    log(24, "POST equipo_id inexistente -> 404", r.status_code == 404)

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["CORTE_ELECTRICO"],
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "evento_energia_id": 99999999,
        "titulo": f"{PREF} bad ev",
        "mensaje": f"{PREF} fk",
    })
    log(25, "POST evento_energia_id inexistente -> 404", r.status_code == 404)

    conn = pg()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.alarmas WHERE titulo LIKE %s", (f"%{PREF}%",))
    n_ok = cur.fetchone()[0]
    cur.close()
    conn.close()
    log(26, "Transacción: FKs inválidas no insertan (count==4)", n_ok == 4, f"n={n_ok}")

    r = requests.get(f"{BASE}/api/v1/alarmas/", headers=h(tok_a))
    ids_list = [a["id"] for a in r.json()] if r.status_code == 200 else []
    ok = r.status_code == 200 and all(i in ids_list for i in T["alarma_ids"])
    log(27, "GET lista alarmas incluye creadas", ok, f"n={len(ids_list) if r.status_code==200 else '?'}")

    aid = T["alarma_ids"][0]
    r = requests.get(f"{BASE}/api/v1/alarmas/{aid}", headers=h(tok_t))
    log(28, "GET alarma/{id} 200 nested", r.status_code == 200 and r.json().get("id") == aid and "tipo" in r.json())

    r = requests.get(f"{BASE}/api/v1/alarmas/99999999", headers=h(tok_a))
    log(29, "GET alarma inexistente -> 404", r.status_code == 404)

    r = requests.get(f"{BASE}/api/v1/alarmas/?estado_alarma_id={T['estado_seed']['PENDIENTE']}", headers=h(tok_o))
    ok = r.status_code == 200 and all(a["estado"]["nombre"] == "PENDIENTE" for a in r.json()) and len(r.json()) >= 4
    log(30, "GET filtro estado=PENDIENTE", ok, f"n={len(r.json()) if r.status_code==200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/alarmas/?equipo_id={T['equipo_id']}", headers=h(tok_a))
    ok = r.status_code == 200 and any(a["id"] == aid for a in r.json())
    log(31, "GET filtro equipo_id", ok)

    r = requests.put(f"{BASE}/api/v1/alarmas/{aid}", headers=h(tok_a), json={
        "estado_alarma_id": T["estado_seed"]["ATENDIDA"],
        "observaciones": f"{PREF} atendida",
    })
    ok = r.status_code == 200
    if ok:
        d = r.json()
        ok = (d["estado"]["nombre"] == "ATENDIDA"
              and d["atendida_por"] == T["admin_id"]
              and d["fecha_atencion"] is not None)
    log(32, "PUT PENDIENTE→ATENDIDA set atendida_por+fecha_atencion", ok, f"status={r.status_code} body={r.text[:240]}")

    r = requests.put(f"{BASE}/api/v1/alarmas/{aid}", headers=h(tok_t), json={
        "estado_alarma_id": T["estado_seed"]["CERRADA"],
        "observaciones": f"{PREF} cerrada",
    })
    ok = r.status_code == 200 and r.json()["estado"]["nombre"] == "CERRADA" and r.json()["atendida_por"] == T["admin_id"]
    log(33, "PUT ATENDIDA→CERRADA conserva atendida_por original", ok, f"status={r.status_code}")

    futuro = datetime.now(timezone.utc) + timedelta(hours=3)
    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_seed"]["EQUIPO"],
        "nivel_alarma_id": T["nivel_seed"]["BAJA"],
        "fecha_hora": futuro.isoformat(),
        "titulo": f"{PREF} futura",
        "mensaje": f"{PREF} check fecha_atencion",
    })
    ok = r.status_code == 201
    futura_id = None
    if ok:
        futura_id = r.json()["id"]
        T["alarma_ids"].append(futura_id)
    log(34, "POST alarma fecha_hora futura PENDIENTE 201", ok, f"status={r.status_code}")

    r = requests.put(f"{BASE}/api/v1/alarmas/{futura_id}", headers=h(tok_a), json={
        "estado_alarma_id": T["estado_seed"]["ATENDIDA"],
    }) if futura_id else type("R", (), {"status_code": 0, "text": "no id"})()
    log(35, "PUT ATENDIDA con fecha_hora futura -> 422 CHECK", r.status_code == 422, f"status={r.status_code} body={r.text[:200]}")

    if futura_id:
        r = requests.get(f"{BASE}/api/v1/alarmas/{futura_id}", headers=h(tok_a))
        ok = r.status_code == 200 and r.json()["estado"]["nombre"] == "PENDIENTE" and r.json()["atendida_por"] is None
        log(36, "Transacción CHECK: alarma sigue PENDIENTE sin atención", ok)
    else:
        log(36, "Transacción CHECK: alarma sigue PENDIENTE sin atención", False, "no futura_id")

    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_o), json={
        "tipo_alarma_id": T["tipo_seed"]["NIVEL_BIOFLOC"],
        "nivel_alarma_id": T["nivel_seed"]["MEDIA"],
        "lote_id": T["lote_id"],
        "titulo": f"{PREF} floc",
        "mensaje": f"{PREF} operario registra alarma de campo",
    })
    ok = r.status_code == 201
    op_id = None
    if ok:
        op_id = r.json()["id"]
        T["alarma_ids"].append(op_id)
    log(37, "POST alarma OPERARIO 201", ok, f"status={r.status_code}")

    r = requests.put(f"{BASE}/api/v1/alarmas/{op_id}", headers=h(tok_o), json={
        "estado_alarma_id": T["estado_seed"]["ATENDIDA"],
        "observaciones": f"{PREF} operario atiende",
    }) if op_id else type("R", (), {"status_code": 0, "json": lambda: {}})()
    ok = r.status_code == 200 and r.json().get("atendida_por") == T["operario_id"]
    log(38, "PUT ATENDIDA OPERARIO set atendida_por=operario", ok, f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/alertas/stock-bajo", headers=h(tok_a))
    log(39, "Inventario: GET /alertas/stock-bajo intacto (separado)", r.status_code == 200, f"status={r.status_code}")

    conn = pg()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla='alarmas' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n_au_al = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla='tipos_alarma' AND detalle::text LIKE %s", ("%TEST_ALARMA_GENERAL%",))
    n_au_t = cur.fetchone()[0]
    cur.close()
    conn.close()
    log(40, f"Auditoría alarmas n={n_au_al}>=6 y tipos INSERT/UPDATE", n_au_al >= 6 and n_au_t >= 2, f"alarmas={n_au_al} tipos={n_au_t}")

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    ops_al = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/alarmas")}
    ops_tip = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/tipos-alarma")}
    has_del = any("delete" in [x.lower() for x in m] for m in list(ops_al.values()) + list(ops_tip.values()))
    stock = "/api/v1/alertas/stock-bajo" in paths
    log(41, "OpenAPI alarmas GET+POST+PUT, sin DELETE; stock-bajo presente",
        (not has_del) and stock and len(ops_al) >= 2,
        f"ops_al={ops_al} stock_bajo={stock}")

    r = requests.delete(f"{BASE}/api/v1/alarmas/{aid}", headers=h(tok_a))
    log(42, "DELETE alarma no existe (405/404)", r.status_code in (404, 405), f"status={r.status_code}")

    for n, nombre in [(47, "PENDIENTE"), (48, "ATENDIDA"), (49, "CERRADA")]:
        eid = T["estado_seed"][nombre]
        r = requests.put(
            f"{BASE}/api/v1/estados-alarma/{eid}",
            headers=h(tok_a),
            json={"nombre": f"{nombre}_RENOMBRADO"},
        )
        still = requests.get(f"{BASE}/api/v1/estados-alarma/{eid}", headers=h(tok_a))
        still_ok = still.status_code == 200 and still.json().get("nombre") == nombre
        log(n, f"PUT no puede renombrar estado semilla {nombre}",
            r.status_code == 422 and still_ok,
            f"put={r.status_code} nombre={still.json().get('nombre') if still.status_code == 200 else '?'}")

    r = requests.get(f"{BASE}/api/v1/estados-alarma/", headers=h(tok_a))
    nombres_est2 = [e["nombre"] for e in r.json()] if r.status_code == 200 else []
    log(50, "GET estados-alarma sigue PENDIENTE/ATENDIDA/CERRADA",
        r.status_code == 200 and {"PENDIENTE", "ATENDIDA", "CERRADA"}.issubset(set(nombres_est2)),
        f"nombres={nombres_est2}")

    conn = pg()
    cur = conn.cursor()
    cur.execute("""
        SELECT table_type, count(*) FROM information_schema.tables
        WHERE table_schema='biofloc' GROUP BY table_type
    """)
    rows = dict(cur.fetchall())
    base_n, view_n = rows.get("BASE TABLE", 0), rows.get("VIEW", 0)
    cur.close()
    conn.close()
    log(43, "PostgreSQL 42 BASE TABLE + 4 VIEW = 46", base_n == 42 and view_n == 4, f"BASE={base_n} VIEW={view_n}")

    root = pathlib.Path(__file__).resolve().parents[2]
    sql_path = root / "database" / "biofloc_erp_v1_1_schema_final.sql"
    sha = hashlib.sha256(sql_path.read_bytes()).hexdigest() if sql_path.exists() else ""
    log(44, "DDL SHA-256 intacto", sha == DDL_SHA, f"got={sha}")

    app_dir = root / "backend" / "app"
    hits = []
    for p in app_dir.rglob("*.py"):
        if "create_all" in p.read_text(encoding="utf-8", errors="replace"):
            hits.append(str(p.relative_to(root)))
    log(45, "create_all() = 0", hits == [], f"hits={hits}")

    try:
        conn = pg()
        cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='tipos_alarma' AND detalle::text LIKE %s", ("%TEST_ALARMA_GENERAL_TIPO%",))
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='niveles_alarma' AND detalle::text LIKE %s", ("%TAG_NIVEL%",))
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estados_alarma' AND detalle::text LIKE %s", ("%TAG_ESTADO%",))
        if T["alarma_ids"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='alarmas' AND registro_id = ANY(%s)", (T["alarma_ids"],))
            cur.execute("DELETE FROM biofloc.alarmas WHERE id = ANY(%s)", (T["alarma_ids"],))
        cur.execute("DELETE FROM biofloc.alarmas WHERE titulo LIKE %s OR mensaje LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
        if T["evento_id"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='eventos_energia' AND registro_id=%s", (T["evento_id"],))
            cur.execute("DELETE FROM biofloc.eventos_energia WHERE id=%s", (T["evento_id"],))
        if T["equipo_id"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='equipos' AND registro_id=%s", (T["equipo_id"],))
            cur.execute("DELETE FROM biofloc.equipos WHERE id=%s", (T["equipo_id"],))
        if T["tipo_extra_id"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='tipos_alarma' AND registro_id=%s", (T["tipo_extra_id"],))
            cur.execute("DELETE FROM biofloc.tipos_alarma WHERE id=%s", (T["tipo_extra_id"],))
        if T["nivel_extra_id"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='niveles_alarma' AND registro_id=%s", (T["nivel_extra_id"],))
            cur.execute("DELETE FROM biofloc.niveles_alarma WHERE id=%s", (T["nivel_extra_id"],))
        if T["estado_extra_id"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estados_alarma' AND registro_id=%s", (T["estado_extra_id"],))
            cur.execute("DELETE FROM biofloc.estados_alarma WHERE id=%s", (T["estado_extra_id"],))
        conn.commit()
        cur.execute("SELECT count(*) FROM biofloc.alarmas WHERE titulo LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        nau = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.tipos_alarma WHERE nombre=%s", ("TEST_ALARMA_GENERAL_TIPO",))
        nt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.niveles_alarma WHERE nombre=%s", ("TAG_NIVEL",))
        nn = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.estados_alarma WHERE nombre=%s", ("TAG_ESTADO",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.tipos_alarma WHERE nombre IN ('CORTE_ELECTRICO','EQUIPO','INVENTARIO_BAJO')")
        ns = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        neq = cur.fetchone()[0]
        cur.close()
        conn.close()
        log(46, f"Limpieza 0 residuales a={na} au={nau} extra={nt+nn+ne} eq={neq}; semillas tipos={ns}",
            na == 0 and nau == 0 and nt == 0 and nn == 0 and ne == 0 and neq == 0 and ns == 3)
    except Exception as e:
        log(46, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
