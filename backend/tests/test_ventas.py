#!/usr/bin/env python3
"""FASE 9B — VENTAS (FINANZAS COMERCIALES SIN movimientos_inventario).

Decisión arquitectónica (OPCIÓN 3):
  VENTA -> DETALLES_VENTA -> LOTES (lote_id NOT NULL).
  NO se generan movimientos_inventario.
  NO existe producto_id en la cadena Ventas (DDL).

Casos:
  - Health + JWT (ADMIN / TEC / OP).
  - 403 sin JWT.
  - Venta 1 detalle (lote real id=1, server-side subtotal/total).
  - Venta múltiples detalles 3 items, total = Σ subtotales.
  - Subtotal y total SERVER-SIDE (cliente envía sólo cant + precio_unit).
  - Detalle vacío => 422.
  - Cantidad <= 0 => 422.
  - Precio_unitario < 0 => 422.
  - Lote inexistente 404.
  - Lote inexistente en detalle #2 de 3 → ROLLBACK ATÓMICO 0 huellas (sin venta ni detalles ni auditoría parcial).
  - GET listado filtros fecha/cliente/lote_id.
  - GET detalle id 200 + detalles anidados + total correcto.
  - GET id no existente → 404.
  - RBAC: OPERARIO puede leer/crear ventas (finanzas comerciales).
  - Auditoría: 1 fila venta INSERT + N filas detalles_venta INSERT por cada venta.
  - Inmutabilidad Venta: OpenAPI sin PUT/PATCH/DELETE.
  - NO hay movimientos_inventario creados (assert count=0 para prefijo).
Limpieza: auditoria → detalles_venta → ventas.
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

SCH = "biofloc"

PREF = "[TEST_VENTA]"
T = {
    "ventas_ids": [],
    "lote_real": None,  # se resuelve por API dinámicamente
    "lote_falso": 99999999,
}

PASS_ICON = "[OK]"
FAIL_ICON = "[FAIL]"
R = []

def log(n, name, ok, d=""):
    icon = PASS_ICON if ok else FAIL_ICON
    if isinstance(n, int):
        n_str = f"{n:02d}"
    else:
        n_str = str(n)
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

# =========================== BLOQUE I INFRA ==================================
def t01_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok"
    log(1, "GET /health ok", ok, str(r.json()))

def t02_login_roles():
    toks = {}
    for k, c, p in [("adm", ADMIN_USER, ADMIN_PASS),
                    ("tec", TECNICO_USER, TECNICO_PASS),
                    ("op", OPERARIO_USER, OPERARIO_PASS)]:
        t = login(c, p)
        toks[k] = t
    ok = all(toks.values())
    log(2, "Login 3 roles JWT", ok, "todos con token" if ok else str(toks))
    return toks["adm"], toks["tec"], toks["op"]

def t03_sin_jwt():
    r = requests.get(f"{BASE}/api/v1/ventas/")
    ok = r.status_code == 403
    log(3, "GET ventas sin JWT 403", ok, f"status={r.status_code}")

def t03b_resolver_lote_real(admin_tok):
    r = requests.get(f"{BASE}/api/v1/lotes/", headers=h(admin_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
    if ok:
        T["lote_real"] = r.json()[0]["id"]
    log("3b", f"Resuelto lote_real id={T['lote_real']}", ok,
        f"status={r.status_code} len={len(r.json()) if r.status_code==200 else '?'}")

# =========================== BLOQUE II VENTAS VÁLIDAS ========================
def t04_venta_1_detalle(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} ClienteA",
        "observaciones": f"{PREF} obs 1d",
        "detalles": [
            {"lote_id": T["lote_real"], "cantidad": "10.500", "precio_unitario": "12000.00"}
        ],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    d = f"status={r.status_code} body={r.text[:300]}"
    if ok:
        data = r.json()
        T["ventas_ids"].append(data["id"])
        subtotal_esp = Decimal("10.500") * Decimal("12000.00")  # 126,000.00
        total_ok = Decimal(str(data["total"])).quantize(Decimal("0.01")) == subtotal_esp.quantize(Decimal("0.01"))
        len_ok = len(data["detalles"]) == 1
        sub_ok = Decimal(str(data["detalles"][0]["subtotal"])).quantize(Decimal("0.01")) == subtotal_esp.quantize(Decimal("0.01"))
        lote_ok = data["detalles"][0]["lote_id"] == T["lote_real"]
        ok = total_ok and len_ok and sub_ok and lote_ok
        d = (f"id={data['id']} total={data['total']} sub1={data['detalles'][0]['subtotal']} "
             f"esp_sub={subtotal_esp} cliente={data['cliente']}")
    log(4, "POST venta 1 detalle (server-side subtotal/total)", ok, d)

def t05_venta_multiples_detalles(admin_tok):
    L = T["lote_real"]
    body = {
        "fecha": (date.today() - timedelta(days=2)).isoformat(),
        "cliente": f"{PREF} ClienteMulti",
        "observaciones": f"{PREF} obs multi 3",
        "detalles": [
            {"lote_id": L, "cantidad": "2.000", "precio_unitario": "10000.00"},   # 20,000
            {"lote_id": L, "cantidad": "1.500", "precio_unitario": "20000.00"},   # 30,000
            {"lote_id": L, "cantidad": "10.000", "precio_unitario": "1500.50"},   # 15,005.00
        ],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    d = f"status={r.status_code}"
    if ok:
        data = r.json()
        T["ventas_ids"].append(data["id"])
        tot_esp = sum((Decimal(x["cantidad"]) * Decimal(x["precio_unitario"]) for x in body["detalles"]), Decimal(0))
        ok = (Decimal(str(data["total"])).quantize(Decimal("0.01")) == tot_esp.quantize(Decimal("0.01"))
              and len(data["detalles"]) == 3)
        d = f"id={data['id']} total={data['total']} esp={tot_esp} n={len(data['detalles'])}"
    log(5, "POST venta 3 detalles total Σ subtotales", ok, d)

def t06_subtotal_y_total_son_servidor(admin_tok):
    """Cliente NO envía subtotal ni total en body (solo cant + p_unit) pero los recibe calculados."""
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} ClienteSoloServ",
        "detalles": [
            {"lote_id": T["lote_real"], "cantidad": "3.000", "precio_unitario": "5000.00"},
        ],
    }
    assert "subtotal" not in body
    assert "total" not in body
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    if ok:
        data = r.json()
        T["ventas_ids"].append(data["id"])
        subtotal_recibido = Decimal(str(data["detalles"][0]["subtotal"]))
        total_recibido = Decimal(str(data["total"]))
        esperado = Decimal("3") * Decimal("5000")
        ok = subtotal_recibido == esperado and total_recibido == esperado
    log(6, "Server-side subtotal/total (cliente no envía)", ok,
        f"status={r.status_code} total={r.json().get('total') if r.status_code==201 else ''}")

# =========================== BLOQUE III VALIDACIONES =========================
def t07_sin_detalles_422(admin_tok):
    body = {"fecha": date.today().isoformat(), "cliente": f"{PREF} C1", "detalles": []}
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(7, "POST venta sin detalles => 422", ok, f"status={r.status_code}")

def t08_cantidad_negativa_422(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} badcant",
        "detalles": [{"lote_id": T["lote_real"], "cantidad": "-1.000", "precio_unitario": "100.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(8, "POST venta cantidad<0 => 422", ok, f"status={r.status_code}")

def t08b_cantidad_cero_422(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} badcant0",
        "detalles": [{"lote_id": T["lote_real"], "cantidad": "0.000", "precio_unitario": "100.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log("8b", "POST venta cantidad=0 => 422", ok, f"status={r.status_code}")

def t09_precio_negativo_422(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} badpu",
        "detalles": [{"lote_id": T["lote_real"], "cantidad": "1.000", "precio_unitario": "-5.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(9, "POST venta p_unit<0 => 422", ok, f"status={r.status_code}")

def t10_lote_inexistente_404(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} badlote",
        "detalles": [{"lote_id": 99999999, "cantidad": "1.000", "precio_unitario": "10.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok = r.status_code == 404
    log(10, "POST venta lote no existe => 404", ok, f"status={r.status_code}")

def t11_rollback_atomico_lote_inexistente_detalle_2(admin_tok):
    """
    Venta con 3 detalles: d1 lote OK, d2 lote FALSO, d3 lote OK.
    Esperado: 404 (por d2), luego verificar 0 huellas.
    """
    pre = {}
    conn = pg(); cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {SCH}.ventas WHERE cliente LIKE %s", (f"%{PREF}%",)); pre["ventas"] = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {SCH}.detalles_venta")
    pre["detalles"] = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {SCH}.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",)); pre["audit"] = cur.fetchone()[0]
    cur.close(); conn.close()

    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} rollback",
        "detalles": [
            {"lote_id": T["lote_real"], "cantidad": "1.000", "precio_unitario": "100.00"},
            {"lote_id": T["lote_falso"], "cantidad": "2.000", "precio_unitario": "100.00"},
            {"lote_id": T["lote_real"], "cantidad": "3.000", "precio_unitario": "100.00"},
        ],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(admin_tok), json=body)
    ok_status = r.status_code == 404

    conn = pg(); cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {SCH}.ventas WHERE cliente LIKE %s", (f"%{PREF}%",)); post_v = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {SCH}.detalles_venta"); post_d = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {SCH}.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",)); post_a = cur.fetchone()[0]
    cur.close(); conn.close()

    # No debe haber restos nuevos
    ok = ok_status and (post_v == pre["ventas"]) and (post_d == pre["detalles"]) and (post_a == pre["audit"])
    log(11, "ROLLBACK atómico detalle #2 inválido = 0 huellas", ok,
        f"s={r.status_code} pre/post: V{pre['ventas']}/{post_v} D{pre['detalles']}/{post_d} A{pre['audit']}/{post_a}")

# =========================== BLOQUE IV GET LISTA + DETALLE ===================
def t12_listar_ventas_filtros(tec_tok):
    url = (f"{BASE}/api/v1/ventas/?cliente={PREF}")
    r = requests.get(url, headers=h(tec_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 3
    log(12, "GET ventas filtro cliente TECNICO", ok,
        f"status={r.status_code} len={len(r.json()) if r.status_code==200 else '?'}")

def t12b_filtro_fecha_y_lote(tec_tok):
    hoy = date.today().isoformat()
    r_fecha = requests.get(
        f"{BASE}/api/v1/ventas/?cliente={PREF}&fecha_desde={hoy}", headers=h(tec_tok),
    )
    r_lote = requests.get(
        f"{BASE}/api/v1/ventas/?lote_id={T['lote_real']}&cliente={PREF}", headers=h(tec_tok),
    )
    ok_fecha = r_fecha.status_code == 200 and len(r_fecha.json()) >= 1
    if ok_fecha:
        ok_fecha = all(v["fecha"] >= hoy for v in r_fecha.json())
    ok_lote = r_lote.status_code == 200 and len(r_lote.json()) >= 3
    if ok_lote:
        ok_lote = all(
            any(d["lote_id"] == T["lote_real"] for d in v["detalles"])
            for v in r_lote.json()
        )
    ok = ok_fecha and ok_lote
    log("12b", "GET ventas filtros fecha_desde + lote_id", ok,
        f"fecha={r_fecha.status_code}/{len(r_fecha.json()) if r_fecha.status_code==200 else '?'} "
        f"lote={r_lote.status_code}/{len(r_lote.json()) if r_lote.status_code==200 else '?'}")

def t13_get_detalle_venta_y_monto(admin_tok):
    v_id = T["ventas_ids"][0]
    r = requests.get(f"{BASE}/api/v1/ventas/{v_id}", headers=h(admin_tok))
    ok = r.status_code == 200
    if ok:
        data = r.json()
        total_esp = Decimal("10.500") * Decimal("12000")
        ok = (data["id"] == v_id
              and Decimal(str(data["total"])).quantize(Decimal("0.01")) == total_esp.quantize(Decimal("0.01"))
              and len(data["detalles"]) == 1
              and data["cliente"].startswith(PREF))
    log(13, "GET ventas/{id} (total + nested detalles)", ok,
        f"status={r.status_code} id={v_id} body={r.text[:300]}")

def t14_get_venta_no_existe(op_tok):
    r = requests.get(f"{BASE}/api/v1/ventas/999999999", headers=h(op_tok))
    ok = r.status_code == 404
    log(14, "GET ventas/NOEXISTE => 404", ok, f"status={r.status_code}")

# =========================== BLOQUE V RBAC ===================================
def t15_operario_crear_venta(op_tok):
    body = {
        "fecha": date.today().isoformat(),
        "cliente": f"{PREF} CreadoOp",
        "detalles": [{"lote_id": T["lote_real"], "cantidad": "0.250", "precio_unitario": "20000.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/ventas/", headers=h(op_tok), json=body)
    ok = r.status_code == 201
    if ok:
        T["ventas_ids"].append(r.json()["id"])
    log(15, "POST venta OPERARIO 201 RBAC", ok,
        f"status={r.status_code} id={r.json().get('id') if r.status_code==201 else ''}")

# =========================== BLOQUE VI AUDITORÍA ============================
def t16_auditoria_ventas_y_detalles():
    conn = pg(); cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {SCH}.auditoria WHERE tabla='ventas' AND accion='INSERT' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n_v = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {SCH}.auditoria WHERE tabla='detalles_venta' AND accion='INSERT' AND detalle::text LIKE %s", (f"%{PREF}%",))
    n_d = cur.fetchone()[0]
    cur.close(); conn.close()
    # Esperado: 4 ventas exitosas (t04, t05, t06, t15) = 4 ventas INSERT audit
    # Detalles: 1+3+1+1 = 6
    ok_ventas = n_v >= 4
    ok_detalles = n_d >= 6
    log(16, f"Auditoría ventas INSERT={n_v}>=4 y detalles_venta INSERT={n_d}>=6",
        ok_ventas and ok_detalles, f"n_v={n_v} n_d={n_d}")

# =========================== BLOQUE VII NO HAY MOVIMIENTOS ===================
def t17_no_hay_movimientos_inventario_generados():
    conn = pg(); cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {SCH}.movimientos_inventario WHERE observaciones::text LIKE %s OR referencia_tipo LIKE %s",
                (f"%{PREF}%", "%VENTA%"))
    n = cur.fetchone()[0]
    cur.close(); conn.close()
    ok = n == 0
    log(17, "0 movimientos_inventario creados en Ventas (decisión OPCIÓN 3)", ok, f"n={n}")

# =========================== BLOQUE VIII OPENAPI (inmutable) =================
def t18_openapi_sin_mutaciones_ventas():
    r = requests.get(f"{BASE}/openapi.json")
    paths = r.json().get("paths", {})
    ops = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/ventas")}
    mal = [(p, m) for p, m in ops.items() if any(x in [x2.lower() for x2 in m] for x in ["put", "delete", "patch"])]
    ok = len(mal) == 0 and len(ops) >= 2
    log(18, "OpenAPI ventas: SOLO GET+POST (inmutable)", ok, f"ops={ops}")

def main():
    print(f"\n{PREF} INICIO suite test_ventas.py\n")
    t01_health()
    tok_a, tok_t, tok_o = t02_login_roles()
    if not (tok_a and tok_t and tok_o):
        print(" ABORT credenciales"); return 1
    t03_sin_jwt()
    t03b_resolver_lote_real(tok_a)
    if not T["lote_real"]:
        print(" ABORT sin lotes reales disponibles"); return 1
    t04_venta_1_detalle(tok_a)
    t05_venta_multiples_detalles(tok_a)
    t06_subtotal_y_total_son_servidor(tok_a)
    t07_sin_detalles_422(tok_a)
    t08_cantidad_negativa_422(tok_a)
    t08b_cantidad_cero_422(tok_a)
    t09_precio_negativo_422(tok_a)
    t10_lote_inexistente_404(tok_a)
    t11_rollback_atomico_lote_inexistente_detalle_2(tok_a)
    t12_listar_ventas_filtros(tok_t)
    t12b_filtro_fecha_y_lote(tok_t)
    t13_get_detalle_venta_y_monto(tok_a)
    t14_get_venta_no_existe(tok_o)
    t15_operario_crear_venta(tok_o)
    t16_auditoria_ventas_y_detalles()
    t17_no_hay_movimientos_inventario_generados()
    t18_openapi_sin_mutaciones_ventas()

    # =========================== LIMPIEZA FK ================================
    try:
        conn = pg(); cur = conn.cursor()
        # auditoria PREF
        cur.execute(f"DELETE FROM {SCH}.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        if T["ventas_ids"]:
            cur.execute(f"DELETE FROM {SCH}.detalles_venta WHERE venta_id IN ({','.join('%s' for _ in T['ventas_ids'])})",
                        tuple(T["ventas_ids"]))
            cur.execute(f"DELETE FROM {SCH}.ventas WHERE id IN ({','.join('%s' for _ in T['ventas_ids'])})",
                        tuple(T["ventas_ids"]))
        conn.commit()
        cur.close(); conn.close()

        conn = pg(); cur = conn.cursor()
        cur.execute(f"SELECT count(*) FROM {SCH}.ventas WHERE cliente LIKE %s", (f"%{PREF}%",)); rv = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {SCH}.detalles_venta WHERE venta_id IN "
                    f"(SELECT id FROM {SCH}.ventas WHERE cliente LIKE %s)", (f"%{PREF}%",)); rd = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {SCH}.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",)); ra = cur.fetchone()[0]
        cur.close(); conn.close()
        ok_clean = rv == 0 and rd == 0 and ra == 0
        log(19, f"Limpieza 0 residuales V={rv} DV={rd} A={ra}", ok_clean, "")
    except Exception as e:
        ok_clean = False
        log(19, f"Limpieza EXCEPTION: {e}", False, "")

    passed = sum(1 for _, _, ok, _ in R if ok)
    total = len(R)
    print(f"\n{PREF} RESUMEN: {passed}/{total} pasadas.")
    return 0 if passed == total else 2

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
