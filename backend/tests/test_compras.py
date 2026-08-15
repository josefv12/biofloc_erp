#!/usr/bin/env python3
"""
FASE 7 — COMPRAS: suite de pruebas (22).
Prueba 200, 201, 403, 404, 422, flujo atómico, stock y auditoría.

Ejecutar desde c:/Users/Jose Fernandez/Documents/biofloc_erp/backend
Servidor levantado en :8000
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

ADMIN_USER = "admin@biofloc.com"
ADMIN_PASS = "AdminBiofloc2026!"
TECNICO_USER = "tecnico_test@biofloc.com"
TECNICO_PASS = "Tecnico1234!"
OPERARIO_USER = "operario_test@biofloc.com"
OPERARIO_PASS = "Operario1234!"

DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")
SCH = "biofloc"

PREF = "[TEST_COMP]"

# ----- IDs temporales creados en esta suite (para limpieza final) -----
T = {
    "cat_id": None,
    "uni_id": None,
    "prods": [],  # [id1, id2, id3]
    "compras": [],
    "movs_inv": [],
    "audit_del": [],
}

PASS_ICON = "[OK]"
FAIL_ICON = "[FAIL]"
R = []


def log(n, name, ok, d=""):
    icon = PASS_ICON if ok else FAIL_ICON
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


# ========================================================================
# BLOQUE I: INFRAESTRUCTURA + AUTENTICACIÓN (1-5)
# ========================================================================
def t01_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok"
    log(1, "GET /health (api+db=ok)", ok, str(r.json()))


def t02_login_admin():
    t = login(ADMIN_USER, ADMIN_PASS)
    ok = t is not None
    log(2, "Login ADMIN", ok, ("..." + t[-12:]) if t else "None")
    return t


def t03_login_tecnico():
    t = login(TECNICO_USER, TECNICO_PASS)
    ok = t is not None
    log(3, "Login TÉCNICO", ok, ("..." + t[-12:]) if t else "None")
    return t


def t04_login_operario():
    t = login(OPERARIO_USER, OPERARIO_PASS)
    ok = t is not None
    log(4, "Login OPERARIO", ok, ("..." + t[-12:]) if t else "None")
    return t


def t05_sin_jwt():
    r = requests.get(f"{BASE}/api/v1/compras/")
    ok = r.status_code == 403
    log(5, "GET compras sin JWT -> 403", ok, f"status={r.status_code}")


# ========================================================================
# BLOQUE II: PRE-REQUISITOS (cat, unidad, 3 productos — usados en la compra)
# ========================================================================
def _asegurar_semilla_inventario(admin_tok):
    """Crear cat + unidad + 3 productos con prefijo [TEST_COMP] si no existen."""
    r = requests.get(f"{BASE}/api/v1/categorias-inventario/", headers=h(admin_tok))
    if r.status_code != 200:
        raise AssertionError(f"GET categorias inventario status={r.status_code}: {r.text[:300]}")
    lista = r.json()
    for c in lista:
        if c["nombre"] == f"{PREF} CAT_INSUMOS":
            T["cat_id"] = c["id"]
            break
    if T["cat_id"] is None:
        r = requests.post(f"{BASE}/api/v1/categorias-inventario/", headers=h(admin_tok),
                          json={"nombre": f"{PREF} CAT_INSUMOS", "descripcion": "Cat pruebas compra", "activo": True})
        if r.status_code != 201:
            raise AssertionError(f"POST cat status={r.status_code}: {r.text[:400]}")
        T["cat_id"] = r.json()["id"]

    r = requests.get(f"{BASE}/api/v1/unidades/", headers=h(admin_tok))
    if r.status_code != 200:
        raise AssertionError(f"GET unidades status={r.status_code}: {r.text[:300]}")
    for u in r.json():
        if u["nombre"] == f"{PREF} UNIDAD_KG":
            T["uni_id"] = u["id"]; break
    if T["uni_id"] is None:
        r = requests.post(f"{BASE}/api/v1/unidades/", headers=h(admin_tok),
                          json={"nombre": f"{PREF} UNIDAD_KG", "simbolo": "TCKG", "activo": True})
        if r.status_code != 201:
            raise AssertionError(f"POST unidad status={r.status_code}: {r.text[:400]}")
        T["uni_id"] = r.json()["id"]

    # 3 productos
    prod_codes = [f"{PREF}-HARINA", f"{PREF}-PROBIOTICO", f"{PREF}-CAL"]
    r = requests.get(f"{BASE}/api/v1/productos/", headers=h(admin_tok))
    if r.status_code != 200:
        raise AssertionError(f"GET productos status={r.status_code}: {r.text[:300]}")
    existente = {p["codigo"]: p["id"] for p in r.json()}
    for cod in prod_codes:
        if cod in existente:
            if existente[cod] not in T["prods"]:
                T["prods"].append(existente[cod])
            continue
        payload = {
            "codigo": cod,
            "nombre": cod.replace(f"{PREF}-", "").lower(),
            "categoria_id": T["cat_id"],
            "unidad_id": T["uni_id"],
            "stock_minimo": 0,
            "activo": True,
        }
        pr = requests.post(f"{BASE}/api/v1/productos/", headers=h(admin_tok), json=payload)
        if pr.status_code != 201:
            raise AssertionError(
                f"POST producto {cod} status={pr.status_code}: "
                f"payload={payload} resp={pr.text[:500]}")
        T["prods"].append(pr.json()["id"])
    assert len(T["prods"]) == 3, f"falló semilla 3 prods, solo {len(T['prods'])} => {T['prods']}"
    return True


# ========================================================================
# BLOQUE III — COMPRAS VÁLIDAS (6-13)
# ========================================================================
def t06_compra_1_detalle(admin_tok):
    p1 = T["prods"][0]
    c = date.today().isoformat()
    body = {
        "fecha": c,
        "proveedor": f"{PREF} Proveedor A",
        "observaciones": f"{PREF} obs1",
        "detalles": [
            {"producto_id": p1, "cantidad": "10.000", "precio_unitario": "2500.00"}
        ],
    }
    # Cliente envía body sin subtotal/total (autoridad solo cantidad*p_u). Intentaremos también
    # enviar total falso 999999 (pero API no lo acepta porque no está en schema Create).
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    detalle_extra = f"status={r.status_code} body={r.text[:300]}"
    if ok:
        data = r.json()
        T["compras"].append(data["id"])
        subtotal_esperado = Decimal("10") * Decimal("2500")  # 25,000.00
        total_ok = Decimal(str(data["total"])) == subtotal_esperado
        detalle_n = len(data["detalles"]) == 1
        subdet_ok = Decimal(str(data["detalles"][0]["subtotal"])) == subtotal_esperado
        ok = total_ok and detalle_n and subdet_ok
        detalle_extra = (f"compra_id={data['id']} total={data['total']} "
                         f"detalles_n={len(data['detalles'])} detalle_subtotal={data['detalles'][0]['subtotal']}")
    log(6, "POST compra 1 detalle (subtotal/total servidor)", ok, detalle_extra)


def t07_compra_multiples_detalles(admin_tok):
    p1, p2, p3 = T["prods"]
    c = (date.today() - timedelta(days=1)).isoformat()
    body = {
        "fecha": c,
        "proveedor": f"{PREF} Proveedor B",
        "observaciones": f"{PREF} obs multi",
        "detalles": [
            {"producto_id": p1, "cantidad": "5.000", "precio_unitario": "2000.00"},
            {"producto_id": p2, "cantidad": "2.500", "precio_unitario": "50000.00"},
            {"producto_id": p3, "cantidad": "100.000", "precio_unitario": "100.00"},
        ],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    d = f"status={r.status_code}"
    if ok:
        data = r.json()
        T["compras"].append(data["id"])
        t_esp = (Decimal("5")*Decimal("2000") +
                 Decimal("2.5")*Decimal("50000") +
                 Decimal("100")*Decimal("100"))
        ok = Decimal(str(data["total"])) == t_esp and len(data["detalles"]) == 3
        d = f"compra_id={data['id']} total={data['total']} esperado={t_esp} n_det={len(data['detalles'])}"
    log(7, "POST compra 3 detalles (total = Σ subtotales)", ok, d)


def t08_movimientos_generados_exactos(admin_tok):
    compra_id = T["compras"][0]
    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.detalles_compra WHERE compra_id=%s", (compra_id,))
    n_det = cur.fetchone()[0]
    cur.execute(
        "SELECT count(*) FROM biofloc.movimientos_inventario "
        "WHERE referencia_tipo='DETALLE_COMPRA' AND referencia_id IN "
        "(SELECT id FROM biofloc.detalles_compra WHERE compra_id=%s)",
        (compra_id,),
    )
    n_mov = cur.fetchone()[0]
    cur.execute(
        "SELECT DISTINCT tipo_movimiento_id FROM biofloc.movimientos_inventario "
        "WHERE referencia_tipo='DETALLE_COMPRA' AND referencia_id IN "
        "(SELECT id FROM biofloc.detalles_compra WHERE compra_id=%s)",
        (compra_id,),
    )
    tipo_ids = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    ok = n_det == n_mov and n_mov == 1 and tipo_ids == [1]
    log(8, "1 detalle = 1 mov ENTRADA (id=1)", ok,
        f"n_det={n_det} n_mov={n_mov} tipos={tipo_ids}")


def t09_referencia_detalle_compra_trazabilidad(admin_tok):
    compra_id = T["compras"][0]
    conn = pg(); cur = conn.cursor()
    cur.execute(
        "SELECT d.id, m.id FROM biofloc.detalles_compra d "
        "JOIN biofloc.movimientos_inventario m "
        "  ON m.referencia_tipo='DETALLE_COMPRA' AND m.referencia_id=d.id "
        "WHERE d.compra_id=%s",
        (compra_id,),
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    ok = len(rows) == 1 and all(x is not None for pair in rows for x in pair)
    log(9, "Trazabilidad JOIN detalle_compra <-> movimiento", ok,
        f"n={len(rows)} rows=[{rows}]")


def t10_stock_incrementado_vista(admin_tok):
    p1 = T["prods"][0]
    conn = pg(); cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(stock_actual,0) FROM biofloc.vista_stock_productos WHERE producto_id=%s",
        (p1,),
    )
    st = cur.fetchone()
    cur.close(); conn.close()
    # Compra1: 10.000; Compra2: 5.000 = total 15.000 para p1
    stock_real = Decimal(str(st[0] if st else 0))
    ok = stock_real >= Decimal("15")
    log(10, "Vista stock_productos refleja compras", ok,
        f"producto_id={p1} stock={stock_real} esperado>=15")


def t11_auditoria_insert_compras_detalles(admin_tok):
    conn = pg(); cur = conn.cursor()
    compra_id = T["compras"][0]
    cur.execute(
        "SELECT count(*) FROM biofloc.auditoria WHERE tabla='compras' AND registro_id=%s AND accion='INSERT'",
        (compra_id,),
    )
    c1 = cur.fetchone()[0]
    cur.execute(
        "SELECT count(*) FROM biofloc.auditoria WHERE tabla='detalles_compra' "
        "AND accion='INSERT' AND registro_id IN "
        "(SELECT id FROM biofloc.detalles_compra WHERE compra_id=%s)",
        (compra_id,),
    )
    c2 = cur.fetchone()[0]
    cur.execute(
        "SELECT count(*) FROM biofloc.auditoria WHERE tabla='movimientos_inventario' "
        "AND accion='INSERT' AND (detalle::jsonb->>'referencia_tipo') = 'DETALLE_COMPRA' "
        "AND (detalle::jsonb->>'referencia_id')::bigint IN "
        "(SELECT id FROM biofloc.detalles_compra WHERE compra_id=%s)",
        (compra_id,),
    )
    c3 = cur.fetchone()[0]
    cur.close(); conn.close()
    ok = c1 >= 1 and c2 == 1 and c3 == 1
    log(11, "Auditoría INSERT 3 capas (compra/detalle/mov)", ok,
        f"compra={c1} detalles={c2} mov_inv={c3}")


def t12_get_listado(admin_tok):
    r = requests.get(f"{BASE}/api/v1/compras/", headers=h(admin_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 2
    log(12, "GET compras lista >= 2 (las 2 creadas)", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


def t13_get_detalle_con_movimientos(admin_tok):
    compra_id = T["compras"][1]  # multi detalle = 3
    r = requests.get(f"{BASE}/api/v1/compras/{compra_id}", headers=h(admin_tok))
    ok = r.status_code == 200
    d = f"status={r.status_code}"
    if ok:
        j = r.json()
        n_mov = len(j.get("movimientos", []))
        n_det = len(j.get("detalles", []))
        ok = n_mov == 3 and n_det == 3
        d = f"id={j.get('id')} detalles={n_det} movs={n_mov}"
    log(13, "GET compra/{id} devuelve 3 detalles + 3 movimientos asociados", ok, d)


# ========================================================================
# BLOQUE IV — FILTROS GET (14)
# ========================================================================
def t14_filtros_get(admin_tok):
    provA = f"{PREF} Proveedor A"
    p1 = T["prods"][0]
    r_a = requests.get(f"{BASE}/api/v1/compras/?proveedor={provA}", headers=h(admin_tok))
    r_b = requests.get(f"{BASE}/api/v1/compras/?producto_id={p1}", headers=h(admin_tok))
    hoy = date.today().isoformat()
    r_c = requests.get(f"{BASE}/api/v1/compras/?fecha_desde={hoy}&fecha_hasta={hoy}", headers=h(admin_tok))
    ok = (r_a.status_code == 200 and len(r_a.json()) >= 1 and
          r_b.status_code == 200 and len(r_b.json()) >= 2 and
          r_c.status_code == 200 and len(r_c.json()) >= 1)
    log(14, "Filtros combinados AND (proveedor + producto + fechas)", ok,
        f"provA={len(r_a.json()) if r_a.status_code==200 else -1} "
        f"prod1={len(r_b.json()) if r_b.status_code==200 else -1} "
        f"hoy={len(r_c.json()) if r_c.status_code==200 else -1}")


# ========================================================================
# BLOQUE V — VALIDACIONES 404 + 422 + RBAC (15-20)
# ========================================================================
def t15_producto_inexistente_404(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "detalles": [{"producto_id": 99999999, "cantidad": "1.000", "precio_unitario": "10.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 404
    log(15, "Producto inexistente → 404", ok, f"status={r.status_code} body={r.text[:200]}")


def t16_cantidad_invalida_422(admin_tok):
    p1 = T["prods"][0]
    body = {
        "fecha": date.today().isoformat(),
        "detalles": [{"producto_id": p1, "cantidad": "0", "precio_unitario": "10.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(16, "Cantidad ≤ 0 → 422", ok, f"status={r.status_code}")


def t17_precio_invalido_422(admin_tok):
    p1 = T["prods"][0]
    body = {
        "fecha": date.today().isoformat(),
        "detalles": [{"producto_id": p1, "cantidad": "1", "precio_unitario": "-1"}],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(17, "Precio_unitario < 0 → 422", ok, f"status={r.status_code}")


def t18_detalles_vacio_422(admin_tok):
    body = {"fecha": date.today().isoformat(), "detalles": []}
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    ok = r.status_code == 422
    log(18, "Detalles vacíos → 422", ok, f"status={r.status_code}")


def t19_rbac_operario_crea_ok(oper_tok):
    p1 = T["prods"][0]
    body = {
        "fecha": date.today().isoformat(),
        "proveedor": f"{PREF} RolOperario",
        "detalles": [{"producto_id": p1, "cantidad": "2.000", "precio_unitario": "100.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(oper_tok), json=body)
    ok = r.status_code == 201
    if ok:
        T["compras"].append(r.json()["id"])
    log(19, "RBAC: OPERARIO puede crear (201)", ok,
        f"status={r.status_code} id={r.json().get('id') if r.status_code==201 else 'N/A'}")


def t20_producto_inactivo_422(admin_tok):
    p2 = T["prods"][1]
    # Desactivar
    requests.put(f"{BASE}/api/v1/productos/{p2}", headers=h(admin_tok), json={"activo": False})
    body = {
        "fecha": date.today().isoformat(),
        "detalles": [{"producto_id": p2, "cantidad": "1.000", "precio_unitario": "10.00"}],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    # Re-activar
    requests.put(f"{BASE}/api/v1/productos/{p2}", headers=h(admin_tok), json={"activo": True})
    ok = r.status_code == 422
    log(20, "Producto inactivo → 422 (luego reactivado)", ok, f"status={r.status_code}")


# ========================================================================
# BLOQUE VI — INMUTABILIDAD + ROLLBACK (21-22)
# ========================================================================
def t21_put_delete_no_existen(admin_tok):
    cid = T["compras"][0]
    rp = requests.put(f"{BASE}/api/v1/compras/{cid}", headers=h(admin_tok),
                      json={"fecha": date.today().isoformat(), "detalles": []})
    rd = requests.delete(f"{BASE}/api/v1/compras/{cid}", headers=h(admin_tok))
    # FastAPI devuelve 405 si el método no está registrado; 404 si ruta no existe
    ok = (rp.status_code in (404, 405)) and (rd.status_code in (404, 405))
    log(21, "PUT / DELETE compras NO implementados (404/405)", ok,
        f"put={rp.status_code} del={rd.status_code}")


def t22_rollback_atomico_sin_huellas(admin_tok):
    # Contamos antes
    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.compras c WHERE c.proveedor LIKE %s", (f"%{PREF}ROLL%",))
    compras_antes = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM biofloc.movimientos_inventario m WHERE m.observaciones LIKE %s", (f"%{PREF}ROLL%",))
    movs_antes = cur.fetchone()[0]
    cur.close(); conn.close()

    # P3 activo antes; intentamos compra con producto_id=99999999 en 2do detalle (forzar fallo)
    # La transacción de crear_compra debe hacer rollback sin dejar nada.
    p1 = T["prods"][0]
    body = {
        "fecha": date.today().isoformat(),
        "proveedor": f"{PREF} ROLLBACK ATÓMICO",
        "observaciones": f"{PREF} ROLLBACK",
        "detalles": [
            {"producto_id": p1, "cantidad": "3.000", "precio_unitario": "50.00"},
            {"producto_id": 9999999999, "cantidad": "1.000", "precio_unitario": "50.00"},  # 404
        ],
    }
    r = requests.post(f"{BASE}/api/v1/compras/", headers=h(admin_tok), json=body)
    # R debe ser 404 (producto 2 no existe). Ahora comprobamos que no haya insertado nada.
    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.compras c WHERE c.proveedor LIKE %s", (f"%{PREF}ROLL%",))
    compras_despues = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM biofloc.movimientos_inventario m WHERE m.observaciones LIKE %s", (f"%{PREF}ROLL%",))
    movs_despues = cur.fetchone()[0]
    cur.close(); conn.close()

    ok = (r.status_code == 404 and
          compras_antes == compras_despues and
          movs_antes == movs_despues)
    log(22, "Rollback atómico: 0 huellas parciales post-fallo (404)", ok,
        f"status_resp={r.status_code} | "
        f"compras:{compras_antes}→{compras_despues}  movs:{movs_antes}→{movs_despues}")


# ========================================================================
# LIMPIEZA FINAL
# ========================================================================
def limpieza(admin_tok):
    print("\n--- LIMPIEZA ---")
    conn = pg(); cur = conn.cursor()

    # Borrar movimientos inventario asociados a los detalles_compra PREF
    # No tenemos router DELETE mov_inv (inmutables). Borrar SQL directo EN ORDEN:
    # auditoría mov_inv → mov_inv → auditoría detalle_compra → detalle_compra → auditoría compra → compra
    for cid in T["compras"]:
        cur.execute(
            "SELECT id FROM biofloc.detalles_compra WHERE compra_id=%s", (cid,),
        )
        det_ids = [r[0] for r in cur.fetchall()]
        if det_ids:
            # 1) auditoría movimientos_inventario asociados
            cur.execute(
                "DELETE FROM biofloc.auditoria WHERE tabla='movimientos_inventario' "
                "AND (detalle::jsonb->>'referencia_tipo')='DETALLE_COMPRA' "
                "AND (detalle::jsonb->>'referencia_id')::bigint = ANY(%s::bigint[])",
                (det_ids,),
            )
            # 2) movimientos_inventario
            cur.execute(
                "DELETE FROM biofloc.movimientos_inventario WHERE "
                "referencia_tipo='DETALLE_COMPRA' AND referencia_id = ANY(%s::bigint[])",
                (det_ids,),
            )
            # 3) auditoría detalles_compra
            cur.execute(
                "DELETE FROM biofloc.auditoria WHERE tabla='detalles_compra' "
                "AND registro_id = ANY(%s::bigint[])",
                (det_ids,),
            )
        # 4) auditoría compra
        cur.execute(
            "DELETE FROM biofloc.auditoria WHERE tabla='compras' AND registro_id=%s",
            (cid,),
        )
        # 5) compra — FK ON DELETE CASCADE quita detalles_compra también
        cur.execute("DELETE FROM biofloc.compras WHERE id=%s", (cid,))

    # Eliminar 3 productos (después compra → detalle → mov)
    for pid in T["prods"]:
        # auditorías asociadas a mov_inv producto también podrían existir (compras las borramos arriba, manualmente)
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='movimientos_inventario' "
                    "AND (detalle::jsonb->>'producto_id')::bigint = %s", (pid,))
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='productos' AND registro_id=%s", (pid,))
        cur.execute("DELETE FROM biofloc.movimientos_inventario WHERE producto_id=%s", (pid,))
        cur.execute("DELETE FROM biofloc.detalles_compra WHERE producto_id=%s", (pid,))
        try:
            cur.execute("DELETE FROM biofloc.productos WHERE id=%s", (pid,))
        except Exception as ex:
            print(f"   WARN no pudo borrar producto {pid}: {ex}")

    if T["cat_id"]:
        try:
            cur.execute("DELETE FROM biofloc.categorias_inventario WHERE id=%s", (T["cat_id"],))
        except Exception as ex:
            print(f"   WARN cat: {ex}")
    if T["uni_id"]:
        try:
            cur.execute("DELETE FROM biofloc.unidades WHERE id=%s", (T["uni_id"],))
        except Exception as ex:
            print(f"   WARN unidad: {ex}")

    conn.commit(); cur.close(); conn.close()
    print("   HECHO.")


# ========================================================================
# MAIN
# ========================================================================
def main():
    print("=" * 70)
    print(" FAZA 7 — PRUEBAS COMPRAS (22)")
    print("=" * 70)
    t01_health()
    at = t02_login_admin()
    tt = t03_login_tecnico()
    ot = t04_login_operario()
    t05_sin_jwt()

    # Semilla
    try:
        _asegurar_semilla_inventario(at)
    except Exception as ex:
        print(f"  FATAL semilla inventario: {ex}"); return

    # Bloque III
    t06_compra_1_detalle(at)
    t07_compra_multiples_detalles(at)
    t08_movimientos_generados_exactos(at)
    t09_referencia_detalle_compra_trazabilidad(at)
    t10_stock_incrementado_vista(at)
    t11_auditoria_insert_compras_detalles(at)
    t12_get_listado(at)
    t13_get_detalle_con_movimientos(at)
    t14_filtros_get(at)
    t15_producto_inexistente_404(at)
    t16_cantidad_invalida_422(at)
    t17_precio_invalido_422(at)
    t18_detalles_vacio_422(at)
    t19_rbac_operario_crea_ok(ot)
    t20_producto_inactivo_422(at)
    t21_put_delete_no_existen(at)
    t22_rollback_atomico_sin_huellas(at)

    # Limpieza
    try:
        limpieza(at)
    except Exception as ex:
        print(f"   Error limpieza: {ex}")

    total = len(R)
    ok = sum(1 for x in R if x[2])
    fail = total - ok
    print("\n" + "=" * 70)
    print(f"  RESULTADO FINAL: {ok}/{total} APROBADOS  |  FALLOS: {fail}")
    print("=" * 70)
    for n, name, is_ok, d in R:
        if not is_ok:
            print(f"  FALLO: [{n:02d}] {name}\n       {d[:400]}")


if __name__ == "__main__":
    main()
