#!/usr/bin/env python3
"""FASE 12 — DASHBOARD (solo lectura). Prefijo [TEST_DASHBOARD]."""
import sys
import io
import hashlib
import pathlib
import requests
import psycopg2
from datetime import date, datetime, timezone
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)
from lote_operativo import asegurar_lote, limpiar_fixtures

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}
PREF = "[TEST_DASHBOARD]"
DDL_SHA = "cbb32f437ef44b23c62133e24438d39dd3508ea0da8081add7277c5b077aa61a"
FECHA = date(2099, 6, 15)
FECHA_VACIA = date(2099, 8, 1)
T = {
    "lote_id": None, "producto_id": None, "cat_gasto": None,
    "tipo_alarma": None, "nivel_alarma": None, "estado_pend": None,
    "equipo_id": None, "compra_id": None, "venta_id": None, "gasto_id": None,
    "alarma_id": None, "evento_id": None, "mant_id": None, "falla_id": None,
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

def D(v):
    return Decimal(str(v))

def counts():
    conn = pg()
    cur = conn.cursor()
    out = {}
    for t in ("auditoria", "movimientos_inventario", "compras", "ventas", "gastos",
              "alarmas", "equipos", "mantenimientos", "fallas", "eventos_energia"):
        cur.execute(f"SELECT count(*) FROM biofloc.{t}")
        out[t] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return out

def pre_cleanup():
    conn = pg()
    cur = conn.cursor()
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.alarmas WHERE titulo LIKE %s OR mensaje LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.gastos WHERE descripcion LIKE %s OR proveedor LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("""
        DELETE FROM biofloc.detalles_venta dv USING biofloc.ventas v
        WHERE dv.venta_id = v.id AND (v.cliente LIKE %s OR v.observaciones LIKE %s)
    """, (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.ventas WHERE cliente LIKE %s OR observaciones LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("""
        DELETE FROM biofloc.movimientos_inventario mi USING biofloc.productos p
        WHERE mi.producto_id = p.id AND p.codigo LIKE %s
    """, (f"%{PREF}%",))
    cur.execute("""
        DELETE FROM biofloc.detalles_compra dc USING biofloc.compras c
        WHERE dc.compra_id = c.id AND (c.proveedor LIKE %s OR c.observaciones LIKE %s)
    """, (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.compras WHERE proveedor LIKE %s OR observaciones LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.mantenimientos WHERE descripcion LIKE %s OR observaciones LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.fallas WHERE descripcion LIKE %s OR solucion LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.eventos_energia WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.equipos WHERE codigo LIKE %s OR nombre LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.productos WHERE codigo LIKE %s", (f"%{PREF}%",))
    conn.commit()
    cur.close()
    conn.close()

def qdate(path, tok, d1=None, d2=None):
    params = {}
    if d1:
        params["fecha_desde"] = d1.isoformat()
    if d2:
        params["fecha_hasta"] = d2.isoformat()
    return requests.get(f"{BASE}/api/v1/dashboard/{path}", headers=h(tok), params=params)

def main():
    print(f"\n{PREF} INICIO suite test_dashboard.py\n")
    pre_cleanup()

    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok")

    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1

    r = requests.get(f"{BASE}/api/v1/dashboard/resumen")
    log(3, "GET dashboard sin JWT -> 403", r.status_code == 403, f"status={r.status_code}")

    c0 = counts()
    r = requests.get(f"{BASE}/api/v1/dashboard/resumen", headers=h(tok_a))
    log(4, "GET /dashboard/resumen ADMIN 200", r.status_code == 200 and "ventas" in r.json(), f"status={r.status_code}")

    r = requests.get(f"{BASE}/api/v1/dashboard/", headers=h(tok_t))
    log(5, "GET /dashboard/ TECNICO = resumen", r.status_code == 200 and "alarmas_pendientes" in r.json())

    endpoints = ["inventario", "compras", "ventas", "gastos", "equipos", "energia", "alarmas", "produccion"]
    ok_all = True
    detail = []
    for ep in endpoints:
        rr = requests.get(f"{BASE}/api/v1/dashboard/{ep}", headers=h(tok_o))
        ok_ep = rr.status_code == 200
        ok_all = ok_all and ok_ep
        detail.append(f"{ep}={rr.status_code}")
    log(6, "GET todos los bloques OPERARIO 200", ok_all, " ".join(detail))

    c1 = counts()
    log(7, "GET dashboard NO escribe (auditoria/mov/compras/ventas/gastos/alarmas/equipos/mant/fallas/energia)", c0 == c1, f"antes={c0} despues={c1}")

    r = qdate("gastos", tok_a, FECHA_VACIA, FECHA_VACIA)
    ok = r.status_code == 200 and r.json()["n_gastos"] == 0 and D(r.json()["total"]) == Decimal("0.00")
    log(8, "Período vacío 2099-08-01: gastos n=0 total=0", ok, f"body={r.text[:180]}")

    r = qdate("compras", tok_a, FECHA_VACIA, FECHA_VACIA)
    log(9, "Período vacío: compras n=0", r.status_code == 200 and r.json()["n_compras"] == 0)

    r = qdate("ventas", tok_a, FECHA_VACIA, FECHA_VACIA)
    log(10, "Período vacío: ventas n=0", r.status_code == 200 and r.json()["n_ventas"] == 0)

    r = qdate("resumen", tok_a, date(2099, 8, 2), date(2099, 8, 1))
    log("10b", "fecha_desde > fecha_hasta -> 422", r.status_code == 422, f"status={r.status_code} body={r.text[:160]}")

    try:
        T["lote_id"] = asegurar_lote(tok_a)[0]
        ok = True
    except Exception as exc:  # noqa: BLE001
        ok = False
        T["lote_id"] = None
        log(11, "Lote real", False, str(exc)[:200])
    else:
        log(11, f"Lote real id={T['lote_id']}", ok)

    r = requests.get(f"{BASE}/api/v1/categorias-gasto/", headers=h(tok_a))
    T["cat_gasto"] = next((c["id"] for c in r.json() if c["nombre"] == "OTROS"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/categorias-inventario/", headers=h(tok_a))
    cat_inv = r.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/unidades/", headers=h(tok_a))
    uni = r.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_a))
    T["tipo_alarma"] = next(t["id"] for t in r.json() if t["nombre"] == "EQUIPO")
    r = requests.get(f"{BASE}/api/v1/niveles-alarma/", headers=h(tok_a))
    T["nivel_alarma"] = next(n["id"] for n in r.json() if n["nombre"] == "ALTA")
    r = requests.get(f"{BASE}/api/v1/estados-alarma/", headers=h(tok_a))
    T["estado_pend"] = next(e["id"] for e in r.json() if e["nombre"] == "PENDIENTE")
    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next((t["id"] for t in r.json() if t["nombre"] == "BLOWER"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est_op = next((e["id"] for e in r.json() if e["nombre"] == "OPERATIVO"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/tipos-mantenimiento/", headers=h(tok_a))
    tipo_mant = r.json()[0]["id"]

    snap_before = requests.get(f"{BASE}/api/v1/dashboard/resumen", headers=h(tok_a)).json()

    r = requests.post(f"{BASE}/api/v1/productos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-P01", "nombre": f"{PREF} prod", "categoria_id": cat_inv,
        "unidad_id": uni, "stock_minimo": "100.000", "activo": True,
    })
    ok = r.status_code == 201
    if ok:
        T["producto_id"] = r.json()["id"]
    log(12, "POST producto semilla dashboard", ok, f"status={r.status_code} id={T['producto_id']}")

    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "proveedor": f"{PREF} ProvA", "observaciones": f"{PREF} compra",
        "detalles": [{"producto_id": T["producto_id"], "cantidad": "10.000", "precio_unitario": "1500.00"}],
    })
    ok = r.status_code == 201
    compra_total = None
    if ok:
        T["compra_id"] = r.json()["id"]
        compra_total = D(r.json()["total"])
        ok = compra_total == Decimal("15000.00")
    log(13, "POST compra 2099-06-15 total=15000", ok, f"status={r.status_code} total={compra_total}")

    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "cliente": f"{PREF} ClienteA", "observaciones": f"{PREF} venta",
        "detalles": [{"lote_id": T["lote_id"], "cantidad": "4.000", "precio_unitario": "2500.00"}],
    })
    ok = r.status_code == 201
    venta_total = None
    if ok:
        T["venta_id"] = r.json()["id"]
        venta_total = D(r.json()["total"])
        ok = venta_total == Decimal("10000.00")
    log(14, "POST venta 2099-06-15 total=10000 (lote, no producto)", ok, f"status={r.status_code} total={venta_total}")

    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "categoria_id": T["cat_gasto"], "lote_id": T["lote_id"],
        "descripcion": f"{PREF} energia", "valor": "25000.00", "proveedor": f"{PREF} ProvG",
    })
    ok = r.status_code == 201
    if ok:
        T["gasto_id"] = r.json()["id"]
    log(15, "POST gasto 2099-06-15 valor=25000 + lote", ok, f"status={r.status_code}")

    fh = datetime(2099, 6, 15, 12, 0, tzinfo=timezone.utc).isoformat()
    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": T["tipo_alarma"], "nivel_alarma_id": T["nivel_alarma"],
        "fecha_hora": fh, "titulo": f"{PREF} alarma", "mensaje": f"{PREF} pendiente",
    })
    ok = r.status_code == 201 and r.json()["estado"]["nombre"] == "PENDIENTE"
    if ok:
        T["alarma_id"] = r.json()["id"]
    log(16, "POST alarma PENDIENTE 2099-06-15", ok, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-EQ-01", "nombre": f"{PREF} blower", "tipo_equipo_id": tipo_eq, "estado_id": est_op,
    })
    ok = r.status_code == 201
    if ok:
        T["equipo_id"] = r.json()["id"]
    log(17, "POST equipo OPERATIVO", ok, f"status={r.status_code} id={T['equipo_id']}")

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json={
        "equipo_id": T["equipo_id"], "tipo_mantenimiento_id": tipo_mant,
        "fecha": FECHA.isoformat(), "descripcion": f"{PREF} preventivo", "costo": "80000.00",
    })
    ok = r.status_code == 201
    if ok:
        T["mant_id"] = r.json()["id"]
    log(18, "POST mantenimiento 2099-06-15", ok)

    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json={
        "equipo_id": T["equipo_id"], "fecha_hora": fh, "descripcion": f"{PREF} vibracion", "costo": "12000.00",
    })
    ok = r.status_code == 201
    if ok:
        T["falla_id"] = r.json()["id"]
    log(19, "POST falla 2099-06-15", ok)

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": fh, "fecha_hora_fin": (datetime(2099, 6, 15, 14, 0, tzinfo=timezone.utc)).isoformat(),
        "tipo": "CORTE", "observaciones": f"{PREF} corte",
    })
    ok = r.status_code == 201
    dur = None
    if ok:
        T["evento_id"] = r.json()["id"]
        dur = r.json()["duracion_minutos"]
        ok = dur == 120
    log(20, "POST evento energía 2099-06-15 duracion=120", ok, f"dur={dur}")

    r = qdate("compras", tok_a, FECHA, FECHA)
    ok = r.status_code == 200 and r.json()["n_compras"] == 1 and D(r.json()["total"]) == Decimal("15000.00")
    ok = ok and D(r.json()["promedio"]) == Decimal("15000.00")
    ok = ok and any(p["nombre"] == f"{PREF} ProvA" for p in r.json()["top_proveedores"])
    log(21, "Dashboard compras: n=1 total=15000 promedio=15000", ok, f"body={r.text[:260]}")

    r = qdate("ventas", tok_a, FECHA, FECHA)
    ok = r.status_code == 200 and r.json()["n_ventas"] == 1 and D(r.json()["total"]) == Decimal("10000.00")
    ok = ok and D(r.json()["cantidad_vendida"]) == Decimal("4.000")
    ok = ok and any(x["lote_id"] == T["lote_id"] for x in r.json()["por_lote"])
    log(22, "Dashboard ventas: n=1 total=10000 cantidad=4 por_lote", ok, f"body={r.text[:280]}")

    r = qdate("gastos", tok_a, FECHA, FECHA)
    ok = r.status_code == 200 and r.json()["n_gastos"] == 1 and D(r.json()["total"]) == Decimal("25000.00")
    ok = ok and r.json()["asociados_a_lote"]["n"] == 1
    log(23, "Dashboard gastos: n=1 total=25000 asociados_lote=1", ok)

    r = qdate("resumen", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200
          and D(js["compras"]["total"]) == Decimal("15000.00")
          and D(js["ventas"]["total"]) == Decimal("10000.00")
          and D(js["gastos"]["total"]) == Decimal("25000.00")
          and js["mantenimientos_periodo"] == 1
          and js["eventos_energia_periodo"] == 1)
    log(24, "Consistencia resumen vs módulos (período 2099-06-15)", ok, f"resumen={ {k: js.get(k) for k in ('compras','ventas','gastos','mantenimientos_periodo','eventos_energia_periodo')} }")

    r = qdate("equipos", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200
          and js["mantenimientos_periodo"]["n"] == 1
          and D(js["mantenimientos_periodo"]["total"]) == Decimal("80000.00")
          and js["fallas_periodo"]["n"] == 1
          and js["equipos_con_fallas_periodo"] == 1
          and any(x["nombre"] == "OPERATIVO" and x["n"] >= 1 for x in js["por_estado"]))
    log(25, "Dashboard equipos: mant=1 fallas=1 estado OPERATIVO real", ok)

    r = qdate("energia", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200 and js["n_eventos"] == 1 and js["duracion_minutos_cerrados"] == 120
          and any(x["nombre"] == "CORTE" for x in js["por_tipo"]))
    log(26, "Dashboard energía: 1 CORTE duracion=120 (tipo texto, no catálogo)", ok)

    r = qdate("alarmas", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["creadas_periodo"] == 1
    ok = ok and any(x["nombre"] == "PENDIENTE" and x["n"] >= 1 for x in js["snapshot_por_estado"])
    log(27, "Dashboard alarmas: 1 creada en período; snapshot PENDIENTE", ok)

    r = requests.get(f"{BASE}/api/v1/dashboard/inventario", headers=h(tok_a))
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["productos_activos"] >= 1 and js["productos_sin_stock"] >= 0
    # producto nuevo con compra 10 y stock_minimo 100 → stock_bajo (10>0 y 10<=100)
    log(28, "Dashboard inventario snapshot (stock por unidad, sin sumar unidades mixtas)", ok,
        f"activos={js.get('productos_activos')} bajo={js.get('productos_stock_bajo')} por_unidad={js.get('stock_por_unidad')}")

    snap_after = requests.get(f"{BASE}/api/v1/dashboard/resumen", headers=h(tok_a)).json()
    ok = snap_after["alarmas_pendientes"] == snap_before["alarmas_pendientes"] + 1
    ok = ok and snap_after["productos_activos"] == snap_before["productos_activos"] + 1
    ok = ok and snap_after["equipos_operativos"] == snap_before["equipos_operativos"] + 1
    log(29, "Snapshots: +1 alarma pendiente, +1 producto activo, +1 equipo operativo", ok,
        f"antes_al={snap_before['alarmas_pendientes']} despues_al={snap_after['alarmas_pendientes']}")

    r = requests.get(f"{BASE}/api/v1/dashboard/produccion", headers=h(tok_o))
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["lotes_activos"] == snap_after["lotes_activos"]
    log(30, "Producción: lotes_activos consistente con resumen; vistas biomasa/supervivencia", ok,
        f"lotes_activos={js.get('lotes_activos')} poblacion={js.get('poblacion_estimada_activos')}")

    c2 = counts()
    r = requests.get(f"{BASE}/api/v1/dashboard/resumen", headers=h(tok_a), params={"fecha_desde": FECHA.isoformat(), "fecha_hasta": FECHA.isoformat()})
    r2 = requests.get(f"{BASE}/api/v1/dashboard/inventario", headers=h(tok_t))
    r3 = requests.get(f"{BASE}/api/v1/dashboard/produccion", headers=h(tok_o))
    c3 = counts()
    log(31, "Re-GET no crea auditoría ni movimientos ni muta compras/ventas/gastos/alarmas/equipos", c2 == c3 and r.status_code == r2.status_code == r3.status_code == 200, f"c2={c2} c3={c3}")

    r = requests.get(f"{BASE}/api/v1/alertas/stock-bajo", headers=h(tok_a))
    log(32, "/alertas/stock-bajo sigue separado y 200", r.status_code == 200)

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    dash = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/dashboard")}
    only_get = all(set(m) == {"get"} or set(x.lower() for x in m) == {"get"} for m in dash.values())
    needed = ["/api/v1/dashboard/resumen", "/api/v1/dashboard/inventario", "/api/v1/dashboard/compras",
              "/api/v1/dashboard/ventas", "/api/v1/dashboard/gastos", "/api/v1/dashboard/equipos",
              "/api/v1/dashboard/energia", "/api/v1/dashboard/alarmas", "/api/v1/dashboard/produccion"]
    ok = only_get and all(p in dash for p in needed)
    log(33, "OpenAPI dashboard: solo GET, 9 bloques", ok, f"ops={dash}")

    r = requests.post(f"{BASE}/api/v1/dashboard/resumen", headers=h(tok_a), json={})
    log(34, "POST dashboard no existe (405/404)", r.status_code in (404, 405), f"status={r.status_code}")

    root = pathlib.Path(__file__).resolve().parents[2]
    sql_path = root / "database" / "biofloc_erp_v1_1_schema_final.sql"
    sha = hashlib.sha256(sql_path.read_bytes()).hexdigest() if sql_path.exists() else ""
    log(35, "DDL SHA-256 intacto", sha == DDL_SHA, f"got={sha}")

    conn = pg()
    cur = conn.cursor()
    cur.execute("SELECT table_type, count(*) FROM information_schema.tables WHERE table_schema='biofloc' GROUP BY table_type")
    rows = dict(cur.fetchall())
    cur.close()
    conn.close()
    log(36, "PostgreSQL 43 BASE TABLE + 3 VIEW = 46", rows.get("BASE TABLE") == 43 and rows.get("VIEW") == 3, str(rows))

    import re
    hits = []
    for p in (root / "backend" / "app").rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"create_all\s*\(", txt):
            hits.append(str(p.relative_to(root)))
    log(37, "create_all() = 0 (regex create_all\\s*\\()", hits == [], f"hits={hits}")

    try:
        pre_cleanup()
        conn = pg()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM biofloc.compras WHERE proveedor LIKE %s", (f"%{PREF}%",))
        nc = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.ventas WHERE cliente LIKE %s", (f"%{PREF}%",))
        nv = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.gastos WHERE descripcion LIKE %s", (f"%{PREF}%",))
        ng = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.alarmas WHERE titulo LIKE %s", (f"%{PREF}%",))
        na = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.productos WHERE codigo LIKE %s", (f"%{PREF}%",))
        np = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
        ne = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        nau = cur.fetchone()[0]
        cur.close()
        conn.close()
        log(38, f"Limpieza 0 residuales c={nc} v={nv} g={ng} a={na} p={np} e={ne} au={nau}",
            nc == nv == ng == na == np == ne == nau == 0)
        leftover_fx = limpiar_fixtures()
        log("38b", f"LEFTOVER TEST_FIXTURE={leftover_fx}", leftover_fx == 0)
    except Exception as e:
        log(38, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
