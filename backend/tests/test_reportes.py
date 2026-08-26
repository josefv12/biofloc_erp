#!/usr/bin/env python3
"""FASE 13 — REPORTES (solo lectura). Prefijo [TEST_REPORTE]."""
import sys
import io
import hashlib
import pathlib
import re
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
PREF = "[TEST_REPORTE]"
DDL_SHA = "cbb32f437ef44b23c62133e24438d39dd3508ea0da8081add7277c5b077aa61a"
FECHA = date(2099, 7, 20)
FECHA_VACIA = date(2099, 9, 1)
T = {}
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
              "alarmas", "equipos", "alimentaciones"):
        cur.execute(f"SELECT count(*) FROM biofloc.{t}")
        out[t] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return out

def pre_cleanup():
    conn = pg()
    cur = conn.cursor()
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    for tabla, col in (
        ("alimentaciones", "observaciones"),
        ("mediciones_agua", "observaciones"),
        ("mediciones_biofloc", "observaciones"),
        ("aplicaciones_biofloc", "observaciones"),
        ("mantenimientos", "descripcion"),
        ("fallas", "descripcion"),
        ("eventos_energia", "observaciones"),
        ("equipos", "codigo"),
        ("productos", "codigo"),
        ("gastos", "descripcion"),
        ("alarmas", "titulo"),
        ("ventas", "cliente"),
        ("compras", "proveedor"),
    ):
        cur.execute(
            f"""
            DELETE FROM biofloc.auditoria a
            USING biofloc.{tabla} t
            WHERE a.tabla = %s AND a.registro_id = t.id AND t.{col} LIKE %s
            """,
            (tabla, f"%{PREF}%"),
        )
    cur.execute("DELETE FROM biofloc.alimentaciones WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.mediciones_agua WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.mediciones_biofloc WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.aplicaciones_biofloc WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.alarmas WHERE titulo LIKE %s OR mensaje LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.gastos WHERE descripcion LIKE %s OR proveedor LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("""
        DELETE FROM biofloc.detalles_venta dv USING biofloc.ventas v
        WHERE dv.venta_id = v.id AND (v.cliente LIKE %s OR v.observaciones LIKE %s)
    """, (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.ventas WHERE cliente LIKE %s OR observaciones LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("""
        DELETE FROM biofloc.auditoria a
        USING biofloc.movimientos_inventario mi
        JOIN biofloc.productos p ON p.id = mi.producto_id
        WHERE a.tabla = 'movimientos_inventario' AND a.registro_id = mi.id AND p.codigo LIKE %s
    """, (f"%{PREF}%",))
    cur.execute("""
        DELETE FROM biofloc.movimientos_inventario mi USING biofloc.productos p
        WHERE mi.producto_id = p.id AND p.codigo LIKE %s
    """, (f"%{PREF}%",))
    cur.execute("""
        DELETE FROM biofloc.detalles_compra dc USING biofloc.compras c
        WHERE dc.compra_id = c.id AND (c.proveedor LIKE %s OR c.observaciones LIKE %s)
    """, (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.compras WHERE proveedor LIKE %s OR observaciones LIKE %s", (f"%{PREF}%", f"%{PREF}%"))
    cur.execute("DELETE FROM biofloc.mantenimientos WHERE descripcion LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.fallas WHERE descripcion LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.eventos_energia WHERE observaciones LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.equipos WHERE codigo LIKE %s", (f"%{PREF}%",))
    cur.execute("DELETE FROM biofloc.productos WHERE codigo LIKE %s", (f"%{PREF}%",))
    conn.commit()
    cur.close()
    conn.close()

def q(path, tok, d1=None, d2=None, **extra):
    params = dict(extra)
    if d1:
        params["fecha_desde"] = d1.isoformat()
    if d2:
        params["fecha_hasta"] = d2.isoformat()
    return requests.get(f"{BASE}/api/v1/reportes/{path}", headers=h(tok), params=params)

def main():
    print(f"\n{PREF} INICIO suite test_reportes.py\n")
    pre_cleanup()

    r = requests.get(f"{BASE}/health")
    log(1, "GET /health", r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok")

    tok_a = login(ADMIN_USER, ADMIN_PASS)
    tok_t = login(TECNICO_USER, TECNICO_PASS)
    tok_o = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "Login 3 roles JWT", all([tok_a, tok_t, tok_o]))
    if not (tok_a and tok_t and tok_o):
        return 1

    r = requests.get(f"{BASE}/api/v1/reportes/ventas")
    log(3, "GET reportes sin JWT -> 403", r.status_code == 403)

    eps = [
        "ventas", "compras", "gastos", "inventario", "inventario/movimientos",
        "compras-inventario", "produccion", "agua", "biofloc", "alimentacion",
        "equipos", "mantenimientos", "fallas", "energia", "alarmas",
    ]
    c0 = counts()
    ok_all, detail = True, []
    for ep in eps:
        rr = requests.get(f"{BASE}/api/v1/reportes/{ep}", headers=h(tok_o))
        ok_ep = rr.status_code == 200 and "total_registros" in rr.json() and "generado_en" in rr.json()
        ok_all = ok_all and ok_ep
        detail.append(f"{ep}={rr.status_code}")
    log(4, "GET todos los reportes OPERARIO 200 + metadatos", ok_all, " ".join(detail))

    r = requests.get(f"{BASE}/api/v1/reportes/produccion", headers=h(tok_t))
    log(5, "GET produccion TECNICO 200", r.status_code == 200)

    r = requests.get(f"{BASE}/api/v1/reportes/ventas", headers=h(tok_a))
    log(6, "GET ventas ADMIN 200", r.status_code == 200)

    c1 = counts()
    log(7, "GET reportes NO escribe tablas", c0 == c1, f"antes={c0} despues={c1}")

    r = q("gastos", tok_a, FECHA_VACIA, FECHA_VACIA)
    ok = r.status_code == 200 and r.json()["total_registros"] == 0 and r.json()["filas"] == []
    log(8, "Período vacío: gastos 0 filas", ok)

    r = q("ventas", tok_a, date(2099, 9, 2), date(2099, 9, 1))
    log(9, "fecha_desde > fecha_hasta -> 422", r.status_code == 422, f"status={r.status_code}")

    try:
        T["lote_id"] = asegurar_lote(tok_a)[0]
        ok = T["lote_id"] is not None
    except Exception as exc:  # noqa: BLE001
        T["lote_id"] = None
        ok = False
        log(10, "Lote real", False, str(exc)[:200])
    else:
        log(10, f"Lote real id={T['lote_id']}", ok)

    r = requests.get(f"{BASE}/api/v1/categorias-gasto/", headers=h(tok_a))
    cat_g = next((c["id"] for c in r.json() if c["nombre"] == "OTROS"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/categorias-inventario/", headers=h(tok_a))
    cat_i = r.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/unidades/", headers=h(tok_a))
    uni = r.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/tipos-alarma/", headers=h(tok_a))
    tipo_al = next(t["id"] for t in r.json() if t["nombre"] == "EQUIPO")
    r = requests.get(f"{BASE}/api/v1/niveles-alarma/", headers=h(tok_a))
    niv_al = next(n["id"] for n in r.json() if n["nombre"] == "MEDIA")
    r = requests.get(f"{BASE}/api/v1/tipos-equipo/", headers=h(tok_a))
    tipo_eq = next((t["id"] for t in r.json() if t["nombre"] == "BLOWER"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/estados-equipo/", headers=h(tok_a))
    est_eq = next((e["id"] for e in r.json() if e["nombre"] == "OPERATIVO"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/tipos-mantenimiento/", headers=h(tok_a))
    tipo_m = r.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/parametros-agua/", headers=h(tok_a))
    param_id = next((p["id"] for p in r.json() if p["nombre"] == "pH"), r.json()[0]["id"])
    r = requests.get(f"{BASE}/api/v1/tipos-aplicacion-biofloc/", headers=h(tok_a))
    tipo_bio = r.json()[0]["id"] if r.status_code == 200 and r.json() else None

    r = requests.post(f"{BASE}/api/v1/productos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-P01", "nombre": f"{PREF} prod", "categoria_id": cat_i,
        "unidad_id": uni, "stock_minimo": "100.000", "activo": True,
    })
    ok = r.status_code == 201
    T["producto_id"] = r.json()["id"] if ok else None
    log(11, "POST producto semilla", ok)

    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "proveedor": f"{PREF} Prov", "observaciones": f"{PREF} compra",
        "detalles": [{"producto_id": T["producto_id"], "cantidad": "8.000", "precio_unitario": "1000.00"}],
    })
    ok = r.status_code == 201 and D(r.json()["total"]) == Decimal("8000.00")
    T["compra_id"] = r.json()["id"] if r.status_code == 201 else None
    log(12, "POST compra 2099-07-20 total=8000", ok)

    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "cliente": f"{PREF} Cliente", "observaciones": f"{PREF} venta",
        "detalles": [{"lote_id": T["lote_id"], "cantidad": "3.000", "precio_unitario": "4000.00"}],
    })
    ok = r.status_code == 201 and D(r.json()["total"]) == Decimal("12000.00")
    log(13, "POST venta 2099-07-20 (lote, no producto)", ok)

    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(tok_a), json={
        "fecha": FECHA.isoformat(), "categoria_id": cat_g, "lote_id": T["lote_id"],
        "descripcion": f"{PREF} gasto", "valor": "5000.00", "proveedor": f"{PREF} ProvG",
    })
    log(14, "POST gasto 2099-07-20", r.status_code == 201)

    fh = datetime(2099, 7, 20, 10, 0, tzinfo=timezone.utc).isoformat()
    r = requests.post(f"{BASE}/api/v1/alarmas/", headers=h(tok_a), json={
        "tipo_alarma_id": tipo_al, "nivel_alarma_id": niv_al, "fecha_hora": fh,
        "titulo": f"{PREF} alarma", "mensaje": f"{PREF} msg", "lote_id": T["lote_id"],
    })
    log(15, "POST alarma", r.status_code == 201)

    r = requests.post(f"{BASE}/api/v1/equipos/", headers=h(tok_a), json={
        "codigo": f"{PREF}-EQ-01", "nombre": f"{PREF} eq", "tipo_equipo_id": tipo_eq, "estado_id": est_eq,
        "ubicacion": "Sala A",
    })
    T["equipo_id"] = r.json()["id"] if r.status_code == 201 else None
    log(16, "POST equipo", r.status_code == 201)

    r = requests.post(f"{BASE}/api/v1/mantenimientos/", headers=h(tok_a), json={
        "equipo_id": T["equipo_id"], "tipo_mantenimiento_id": tipo_m, "fecha": FECHA.isoformat(),
        "descripcion": f"{PREF} mant", "costo": "9000.00",
    })
    log(17, "POST mantenimiento", r.status_code == 201)

    r = requests.post(f"{BASE}/api/v1/fallas/", headers=h(tok_a), json={
        "equipo_id": T["equipo_id"], "fecha_hora": fh, "descripcion": f"{PREF} falla", "costo": "300.00",
    })
    log(18, "POST falla", r.status_code == 201)

    r = requests.post(f"{BASE}/api/v1/eventos-energia/", headers=h(tok_a), json={
        "fecha_hora_inicio": fh, "tipo": "CORTE", "observaciones": f"{PREF} corte",
    })
    log(19, "POST evento energía", r.status_code == 201)

    r = requests.post(f"{BASE}/api/v1/alimentaciones/", headers=h(tok_a), json={
        "lote_id": T["lote_id"], "producto_id": T["producto_id"], "fecha_hora": fh,
        "cantidad": 2.5, "observaciones": f"{PREF} alimento",
    })
    log(20, "POST alimentación", r.status_code == 201, f"status={r.status_code} {r.text[:160]}")

    r = requests.post(f"{BASE}/api/v1/mediciones-agua/", headers=h(tok_a), json={
        "lote_id": T["lote_id"], "parametro_id": param_id, "fecha_hora": fh,
        "valor": "7.2000", "observaciones": f"{PREF} ph",
    })
    log(21, "POST medición agua", r.status_code == 201, f"status={r.status_code} {r.text[:160]}")

    r = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", headers=h(tok_a), json={
        "lote_id": T["lote_id"], "fecha_hora": fh, "volumen_sedimentable": "12.50",
        "unidad": "mL/L", "observaciones": f"{PREF} floc",
    })
    log(22, "POST medición biofloc", r.status_code == 201, f"status={r.status_code} {r.text[:160]}")

    if tipo_bio:
        r = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/", headers=h(tok_a), json={
            "lote_id": T["lote_id"], "tipo_aplicacion_id": tipo_bio, "fecha_hora": fh,
            "cantidad": "1.0000", "unidad": "kg", "observaciones": f"{PREF} aplic",
        })
        log(23, "POST aplicación biofloc", r.status_code == 201, f"status={r.status_code}")
    else:
        log(23, "POST aplicación biofloc (sin tipo)", False)

    r = q("ventas", tok_a, FECHA, FECHA, cliente=PREF)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200 and js["total_registros"] == 1
          and D(js["suma_subtotales"]) == Decimal("12000.00")
          and js["filas"][0]["lote_id"] == T["lote_id"]
          and "producto_id" not in js["filas"][0])
    log(24, "Reporte ventas: 1 fila lote, suma=12000, SIN producto_id", ok, f"body={str(js)[:240]}")

    r = q("compras", tok_a, FECHA, FECHA, proveedor=PREF)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200 and js["total_registros"] == 1
          and D(js["suma_subtotales"]) == Decimal("8000.00")
          and js["filas"][0]["producto_id"] == T["producto_id"]
          and len(js["cantidad_por_unidad"]) == 1)
    log(25, "Reporte compras: 1 fila producto+unidad, total=8000", ok)

    r = q("gastos", tok_a, FECHA, FECHA, proveedor=PREF)
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] == 1 and D(js["total_valor"]) == Decimal("5000.00")
    ok = ok and js["filas"][0]["lote_id"] == T["lote_id"]
    log(26, "Reporte gastos: 1 fila + lote + total_valor=5000", ok)

    r = q("compras-inventario", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200 and js["total_registros"] >= 1
          and any(f.get("referencia_tipo") == "DETALLE_COMPRA" and f.get("movimiento_id") for f in js["filas"]))
    log(27, "Trazabilidad compra→inventario DETALLE_COMPRA", ok, f"filas={js.get('filas')}")

    r = q("inventario/movimientos", tok_a, None, None, producto_id=T["producto_id"], referencia_tipo="DETALLE_COMPRA")
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] >= 1 and js["filas"][0]["tipo"] == "ENTRADA"
    log(28, "Reporte movimientos: ENTRADA DETALLE_COMPRA", ok)

    r = requests.get(f"{BASE}/api/v1/reportes/inventario", headers=h(tok_a), params={"clasificacion": "STOCK_BAJO"})
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and any(f["producto_id"] == T["producto_id"] for f in js["filas"])
    log(29, "Reporte inventario snapshot STOCK_BAJO incluye producto test", ok,
        f"n={js.get('total_registros')} clasifs={[f['clasificacion'] for f in js.get('filas', [])][:5]}")

    r = q("alimentacion", tok_a, FECHA, FECHA, lote_id=T["lote_id"])
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] >= 1 and D(js["filas"][0]["cantidad"]) == Decimal("2.500")
    ok = ok and "costo" not in js["filas"][0]
    log(30, "Reporte alimentación: cantidad+unidad, SIN costo", ok, f"status={r.status_code}")

    r = q("agua", tok_a, FECHA, FECHA, lote_id=T["lote_id"])
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] >= 1 and "nota" in js and "etapa ACTUAL" in js["nota"]
    log(31, "Reporte agua: medición + nota limitación etapa actual", ok, f"n={js.get('total_registros')}")

    r = q("biofloc", tok_a, FECHA, FECHA, lote_id=T["lote_id"])
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and len(js.get("mediciones", [])) >= 1 and len(js.get("aplicaciones", [])) >= 1
    log(32, "Reporte biofloc: mediciones + aplicaciones", ok)

    r = requests.get(f"{BASE}/api/v1/reportes/produccion", headers=h(tok_a), params={"lote_id": T["lote_id"]})
    js = r.json() if r.status_code == 200 else {}
    ok = (r.status_code == 200 and js["total_registros"] == 1
          and "poblacion_estimada" in js["filas"][0]
          and "fcr" not in js["filas"][0])
    log(33, "Reporte producción: lote + vistas biomasa/supervivencia, SIN FCR", ok)

    r = q("equipos", tok_a)
    ok = r.status_code == 200 and any(f["codigo"] == f"{PREF}-EQ-01" for f in r.json()["filas"])
    log(34, "Reporte equipos incluye equipo test + tipo/estado", ok)

    r = q("mantenimientos", tok_a, FECHA, FECHA, equipo_id=T["equipo_id"])
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] == 1 and D(js["total_costo"]) == Decimal("9000.00")
    log(35, "Reporte mantenimientos: 1 fila costo=9000 (no 'pendiente')", ok)

    r = q("fallas", tok_a, FECHA, FECHA, equipo_id=T["equipo_id"])
    ok = r.status_code == 200 and r.json()["total_registros"] == 1
    log(36, "Reporte fallas: 1 fila", ok)

    r = q("energia", tok_a, FECHA, FECHA, tipo="CORTE")
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] >= 1 and js["filas"][0]["tipo"] == "CORTE"
    log(37, "Reporte energía: tipo texto CORTE (no normalizado)", ok)

    r = q("alarmas", tok_a, FECHA, FECHA)
    js = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and js["total_registros"] >= 1 and js["filas"][0]["lote_id"] == T["lote_id"]
    log(38, "Reporte alarmas: tipo/nivel/estado + lote", ok)

    r = requests.get(f"{BASE}/api/v1/alertas/stock-bajo", headers=h(tok_a))
    log(39, "/alertas/stock-bajo intacto", r.status_code == 200)

    c2 = counts()
    for ep in ("ventas", "compras", "inventario", "produccion", "agua"):
        requests.get(f"{BASE}/api/v1/reportes/{ep}", headers=h(tok_a),
                     params={"fecha_desde": FECHA.isoformat(), "fecha_hasta": FECHA.isoformat()})
    c3 = counts()
    log(40, "Re-GET no crea auditoría ni movimientos", c2 == c3, f"c2={c2} c3={c3}")

    paths = requests.get(f"{BASE}/openapi.json").json().get("paths", {})
    reps = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/reportes")}
    only_get = all(set(x.lower() for x in m) == {"get"} for m in reps.values())
    log(41, "OpenAPI reportes: solo GET", only_get and len(reps) >= 15, f"n={len(reps)}")

    r = requests.post(f"{BASE}/api/v1/reportes/ventas", headers=h(tok_a), json={})
    log(42, "POST reportes no existe (405/404)", r.status_code in (404, 405), f"status={r.status_code}")

    root = pathlib.Path(__file__).resolve().parents[2]
    sha = hashlib.sha256((root / "database" / "biofloc_erp_v1_1_schema_final.sql").read_bytes()).hexdigest()
    log(43, "DDL SHA-256 intacto", sha == DDL_SHA, f"got={sha}")

    conn = pg()
    cur = conn.cursor()
    cur.execute("SELECT table_type, count(*) FROM information_schema.tables WHERE table_schema='biofloc' GROUP BY table_type")
    rows = dict(cur.fetchall())
    cur.close()
    conn.close()
    log(44, "PostgreSQL 43 BASE TABLE + 3 VIEW = 46", rows.get("BASE TABLE") == 43 and rows.get("VIEW") == 3, str(rows))

    hits = []
    for p in (root / "backend" / "app").rglob("*.py"):
        if re.search(r"create_all\s*\(", p.read_text(encoding="utf-8", errors="replace")):
            hits.append(str(p.relative_to(root)))
    log(45, "create_all() = 0", hits == [], f"hits={hits}")

    try:
        pre_cleanup()
        conn = pg()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM biofloc.compras WHERE proveedor LIKE %s", (f"%{PREF}%",))
        nc = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.productos WHERE codigo LIKE %s", (f"%{PREF}%",))
        np = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.alimentaciones WHERE observaciones LIKE %s", (f"%{PREF}%",))
        nal = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.mediciones_agua WHERE observaciones LIKE %s", (f"%{PREF}%",))
        nmw = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        nau = cur.fetchone()[0]
        cur.close()
        conn.close()
        log(46, f"Limpieza 0 residuales c={nc} p={np} al={nal} mw={nmw} au={nau}",
            nc == np == nal == nmw == nau == 0)
        leftover_fx = limpiar_fixtures()
        log("46b", f"LEFTOVER TEST_FIXTURE={leftover_fx}", leftover_fx == 0)
    except Exception as e:
        log(46, f"Limpieza EXCEPTION: {e}", False)

    passed = sum(1 for _, _, ok, _ in R if ok)
    print(f"\n{PREF} RESUMEN: {passed}/{len(R)} pasadas.")
    return 0 if passed == len(R) else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
