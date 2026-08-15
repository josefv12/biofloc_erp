"""
Suite pruebas FASE 8 — ALARMAS DE INVENTARIO.

Uso: cd backend; python tests/test_alertas_inventario.py
22 pruebas, prefijo [TEST_ALARMA], limpieza SQL final.
"""
import sys
import io
from decimal import Decimal

import requests
import psycopg2

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_ALARMA]"

log_ok = 0
log_fail = 0


def log(n, name, ok, detail=""):
    global log_ok, log_fail
    if ok:
        log_ok += 1
        tag = "PASS"
    else:
        log_fail += 1
        tag = "FAIL"
    print(f"{PREF} [{n:02d}] {tag} {name:<62} {str(detail)[:240]}")


def login(correo, clave):
    r = requests.post(BASE + "/api/v1/auth/login", json={"correo": correo, "password": clave}, timeout=30)
    if r.status_code != 200:
        raise AssertionError(f"login fallo {r.status_code}: {r.text[:300]}")
    return "Bearer " + r.json()["access_token"]


ADM_CRED = ("admin@biofloc.com", "AdminBiofloc2026!")
TEC_CRED = ("tecnico_test@biofloc.com", "Tecnico1234!")
OPE_CRED = ("operario_test@biofloc.com", "Operario1234!")


def hdr(tok):
    return {"Authorization": tok, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# BLOQUE I — Infraestructura 1-3
# ---------------------------------------------------------------------------
def bloque1():
    r = requests.get(BASE + "/health", timeout=20)
    log(1, "Health check", r.status_code == 200, r.status_code)


def bloque2():
    try:
        t1 = login(*ADM_CRED)
        t2 = login(*TEC_CRED)
        t3 = login(*OPE_CRED)
        log(2, "Login 3 tokens (admin/tec/oper)", all([t1, t2, t3]), "3 tokens")
        return t1, t2, t3
    except AssertionError as e:
        log(2, "Login 3 tokens", False, str(e)[:200])
        raise


def bloque3():
    r = requests.get(BASE + "/api/v1/alertas/stock-bajo", timeout=20)
    log(3, "Sin JWT -> 403", r.status_code == 403, r.status_code)


# ---------------------------------------------------------------------------
# BLOQUE II — Semilla
# ---------------------------------------------------------------------------
SEED = {}


def semilla(tok):
    r = requests.post(
        BASE + "/api/v1/categorias-inventario",
        json={"nombre": f"{PREF} CAT", "descripcion": "A"},
        headers=hdr(tok),
    )
    if r.status_code not in (200, 201):
        raise AssertionError(f"cat {r.status_code}: {r.text[:300]}")
    cat = r.json()
    SEED["cat"] = cat

    r = requests.post(
        BASE + "/api/v1/unidades",
        json={"nombre": f"{PREF} UNID", "simbolo": "TALU"},
        headers=hdr(tok),
    )
    if r.status_code not in (200, 201):
        raise AssertionError(f"uni {r.status_code}: {r.text[:300]}")
    SEED["uni"] = r.json()

    # sufijo, stock_minimo, stock_actual, activo
    specs = [
        ("A", Decimal("5.000"), Decimal("20.000"), True),
        ("B", Decimal("10.000"), Decimal("10.000"), True),
        ("C", Decimal("15.000"), Decimal("8.000"), True),
        ("D", Decimal("20.000"), Decimal("0.000"), True),
        ("E", Decimal("5.000"), Decimal("3.000"), False),
    ]
    prods = {}
    for suf, smin, sact, active in specs:
        body = {
            "codigo": f"{PREF}-PROD-{suf}",
            "nombre": f"{PREF} Producto {suf}",
            "categoria_id": SEED["cat"]["id"],
            "unidad_id": SEED["uni"]["id"],
            "stock_minimo": float(smin),
            "activo": active,
        }
        r = requests.post(BASE + "/api/v1/productos", json=body, headers=hdr(tok))
        if r.status_code not in (200, 201):
            raise AssertionError(f"prod{suf} {r.status_code}: {r.text[:300]}")
        p = r.json()
        prods[suf] = p
        if sact > 0:
            rm = requests.post(
                BASE + "/api/v1/movimientos-inventario",
                json={
                    "producto_id": p["id"],
                    "tipo_movimiento_id": 1,
                    "cantidad": float(sact),
                    "observaciones": f"{PREF} ENTRADA {suf}",
                },
                headers=hdr(tok),
            )
            if rm.status_code not in (200, 201):
                raise AssertionError(f"mov entrada {suf} {rm.status_code}: {rm.text[:300]}")
    SEED["prods"] = prods


# ---------------------------------------------------------------------------
# Pruebas 4-22
# ---------------------------------------------------------------------------
def pruebas_resto(tok, tok_tec, tok_ope):
    cat_id = SEED["cat"]["id"]
    prods = SEED["prods"]
    pa = prods["A"]
    pb = prods["B"]
    pc = prods["C"]
    pd = prods["D"]
    pe = prods["E"]

    r = requests.get(BASE + "/api/v1/alertas/stock-bajo", headers=hdr(tok))
    log(4, "GET stock-bajo 200", r.status_code == 200, r.status_code)
    rows = r.json()
    ids = {row["producto_id"]: row for row in rows}

    ok5 = (pa["id"] not in ids) and (pb["id"] in ids) and (pc["id"] in ids) and (pd["id"] in ids) and (pe["id"] not in ids)
    log(
        5,
        "NORMAL A fuera + STOCK_BAJO B/C dentro + SIN_STOCK D dentro + E inactivo fuera",
        ok5,
        f"ids_presentes={sorted(ids.keys())}",
    )

    primero = rows[0] if rows else {}
    log(
        6,
        "Orden gravedad 1º = SIN_STOCK",
        bool(rows) and primero["clasificacion"] == "SIN_STOCK" and primero["producto_id"] == pd["id"],
        (primero.get("producto_id"), primero.get("clasificacion")),
    )

    rd = requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pd['id']}", headers=hdr(tok))
    dj = rd.json()
    ok7 = (
        rd.status_code == 200
        and dj["clasificacion"] == "SIN_STOCK"
        and abs(Decimal(str(dj["stock_actual"]))) <= Decimal("0.001")
    )
    log(7, "GET D SIN_STOCK exacto", ok7, f"sa={dj.get('stock_actual')} clas={dj.get('clasificacion')}")

    rb = requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pb['id']}", headers=hdr(tok))
    bj = rb.json()
    ok8 = (
        rb.status_code == 200
        and bj["clasificacion"] == "STOCK_BAJO"
        and Decimal(str(bj["diferencia"])) == Decimal("0.000")
    )
    log(8, "GET B STOCK_BAJO (stock==min) diff=0", ok8, f"sa={bj['stock_actual']} diff={bj['diferencia']} clas={bj['clasificacion']}")

    rinc = requests.get(BASE + "/api/v1/alertas/stock-bajo", params={"incluir_normal": True}, headers=hdr(tok))
    inc_ids = {row["producto_id"]: row for row in rinc.json()}
    ok9 = pa["id"] in inc_ids and inc_ids[pa["id"]]["clasificacion"] == "NORMAL"
    log(9, "incluir_normal=True -> A (NORMAL) aparece", ok9, f"A_normal_presente={pa['id'] in inc_ids}")

    rsin = requests.get(BASE + "/api/v1/alertas/stock-bajo",
                        params={"clasificacion": "SIN_STOCK", "categoria_id": cat_id}, headers=hdr(tok))
    js = rsin.json()
    log(10, "Filtro clasificacion=SIN_STOCK + cat = solo D", len(js) == 1 and js[0]["producto_id"] == pd["id"], f"len={len(js)}")

    rcat = requests.get(BASE + "/api/v1/alertas/stock-bajo", params={"categoria_id": cat_id}, headers=hdr(tok))
    log(11, "Filtro categoria_id -> 3 alarmas activas", len(rcat.json()) == 3, f"len={len(rcat.json())}")

    rpc = requests.get(BASE + "/api/v1/alertas/stock-bajo", params={"producto_id": pc["id"]}, headers=hdr(tok))
    ok12 = len(rpc.json()) == 1 and rpc.json()[0]["producto_id"] == pc["id"] and rpc.json()[0]["clasificacion"] == "STOCK_BAJO"
    log(12, "Filtro producto_id C STOCK_BAJO", ok12, f"len={len(rpc.json())}")

    rnf = requests.get(BASE + "/api/v1/alertas/stock-bajo/999999999", headers=hdr(tok))
    log(13, "Producto inexistente -> 404", rnf.status_code == 404, rnf.status_code)

    rall = requests.get(BASE + "/api/v1/alertas/stock-bajo", params={"solo_activos": False}, headers=hdr(tok))
    ids_all = {row["producto_id"] for row in rall.json()}
    log(14, "solo_activos=False incluye E inactivo", pe["id"] in ids_all, f"len_rall={len(rall.json())} ids={sorted(ids_all)}")

    rope = requests.get(BASE + "/api/v1/alertas/stock-bajo", headers=hdr(tok_ope))
    log(15, "RBAC OPERARIO GET lista OK", rope.status_code == 200 and len(rope.json()) >= 3, f"len={len(rope.json())}")

    rt = requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pc['id']}", headers=hdr(tok_tec))
    log(16, "RBAC TECNICO GET detalle C STOCK_BAJO", rt.status_code == 200 and rt.json()["clasificacion"] == "STOCK_BAJO", rt.status_code)

    fields = [
        "producto_id", "codigo", "nombre", "unidad", "stock_actual", "stock_minimo",
        "diferencia", "clasificacion", "activo", "categoria_id", "categoria_nombre",
    ]
    ok_fields = [f in bj for f in fields]
    log(17, "Campos AlarmaStockOut completos", all(ok_fields), list(bj.keys()))

    rm_out = requests.post(
        BASE + "/api/v1/movimientos-inventario",
        json={"producto_id": pb["id"], "tipo_movimiento_id": 2, "cantidad": 1.0, "observaciones": f"{PREF} SALIDA B -1"},
        headers=hdr(tok),
    )
    rb2 = requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pb['id']}", headers=hdr(tok))
    bj2 = rb2.json()
    ok18 = (
        rm_out.status_code in (200, 201)
        and Decimal(str(bj2["stock_actual"])) == Decimal("9.000")
        and bj2["clasificacion"] == "STOCK_BAJO"
        and Decimal(str(bj2["diferencia"])) == Decimal("-1.000")
    )
    log(18, "Vista refleja SALIDA B: 9 <= 10 (STOCK_BAJO diff -1)", ok18,
        f"sa={bj2['stock_actual']} diff={bj2['diferencia']} clas={bj2['clasificacion']}")

    antes = requests.get(BASE + "/api/v1/movimientos-inventario", headers=hdr(tok), params={"producto_id": pb["id"]})
    for _ in range(5):
        requests.get(BASE + "/api/v1/alertas/stock-bajo", headers=hdr(tok))
    despues = requests.get(BASE + "/api/v1/movimientos-inventario", headers=hdr(tok), params={"producto_id": pb["id"]})
    log(19, "Consultar alarmas NO genera mov nuevos", len(antes.json()) == len(despues.json()),
        f"antes={len(antes.json())} despues={len(despues.json())}")

    # 20: GET no inserta auditoria -> consultas GET /stock-bajo N veces no añaden filas
    DB = dict(host="localhost", port=5432, dbname="biofloc_erp", user="postgres", password="admin")
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    cur.execute("SET search_path TO biofloc")
    cur.execute("SELECT count(*) FROM auditoria WHERE tabla = 'alertas' OR tabla LIKE '%alarma%'")
    n0 = cur.fetchone()[0]
    for _ in range(5):
        requests.get(BASE + "/api/v1/alertas/stock-bajo", headers=hdr(tok))
        requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pc['id']}", headers=hdr(tok))
    cur.execute("SELECT count(*) FROM auditoria WHERE tabla = 'alertas' OR tabla LIKE '%alarma%'")
    n1 = cur.fetchone()[0]
    cur.close(); conn.close()
    log(20, "GET alarma no genera auditoria (lectura)", n0 == n1, f"antes={n0} despues={n1}")

    # 21: clasificacion invalida devuelve 422
    rbad = requests.get(BASE + "/api/v1/alertas/stock-bajo", params={"clasificacion": "CLASIF_INEXISTENTE"}, headers=hdr(tok))
    log(21, "Clasificacion invalida -> 422", rbad.status_code == 422, rbad.status_code)

    # 22: ver que el stock viene de vista_stock (no de producto): repetir 1 entrada a B (10) -> sera 9+10=19 y min=10, NORMAL diff=9. Si endpoint devuelve NORMAL => ok viene sum vista
    rm_in = requests.post(
        BASE + "/api/v1/movimientos-inventario",
        json={"producto_id": pb["id"], "tipo_movimiento_id": 1, "cantidad": 10.0, "observaciones": f"{PREF} ENTRADA2 B +10"},
        headers=hdr(tok),
    )
    rb3 = requests.get(BASE + f"/api/v1/alertas/stock-bajo/{pb['id']}", headers=hdr(tok))
    bj3 = rb3.json()
    ok22 = (
        rm_in.status_code in (200, 201)
        and Decimal(str(bj3["stock_actual"])) == Decimal("19.000")
        and bj3["clasificacion"] == "NORMAL"
        and Decimal(str(bj3["diferencia"])) == Decimal("9.000")
    )
    log(22, "Stock proviene de vista_stock: B +10 = 19 NORMAL", ok22,
        f"sa={bj3['stock_actual']} diff={bj3['diferencia']} clas={bj3['clasificacion']}")


# ---------------------------------------------------------------------------
# Limpieza SQL
# ---------------------------------------------------------------------------
def limpieza():
    cat = SEED.get("cat") and SEED["cat"]["id"]
    uni = SEED.get("uni") and SEED["uni"]["id"]
    pids = [p["id"] for p in (SEED.get("prods") or {}).values()]
    if not pids:
        return
    DB = dict(host="localhost", port=5432, dbname="biofloc_erp", user="postgres", password="admin")
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    cur.execute("SET search_path TO biofloc")
    try:
        cur.execute(
            "DELETE FROM auditoria WHERE detalle::text LIKE %s OR detalle::text LIKE %s",
            (f"%{PREF}%", f"%{PREF}%"),
        )
        cur.execute("DELETE FROM movimientos_inventario WHERE observaciones LIKE %s", (f"%{PREF}%",))
        cur.execute("DELETE FROM auditoria WHERE tabla='productos' AND registro_id = ANY(%s::bigint[])", (pids,))
        cur.execute("DELETE FROM productos WHERE id = ANY(%s::bigint[])", (pids,))
        if cat:
            cur.execute("DELETE FROM auditoria WHERE tabla='categorias_inventario' AND registro_id=%s", (cat,))
            cur.execute("DELETE FROM categorias_inventario WHERE id=%s", (cat,))
        if uni:
            cur.execute("DELETE FROM auditoria WHERE tabla='unidades' AND registro_id=%s", (uni,))
            cur.execute("DELETE FROM unidades WHERE id=%s", (uni,))
        conn.commit()
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tok_adm = tok_tec = tok_ope = None
    try:
        print("=" * 70)
        print(f"{PREF} SUITE ALARMAS DE INVENTARIO — 22 PRUEBAS")
        print("=" * 70)
        bloque1()
        tok_adm, tok_tec, tok_ope = bloque2()
        bloque3()
        print(f"{PREF} --- Semilla cat/unid/5 prods + movs ---")
        semilla(tok_adm)
        print(f"{PREF} --- Ejecutando pruebas 4-22 ---")
        pruebas_resto(tok_adm, tok_tec, tok_ope)
    except Exception as e:
        import traceback
        print(f"{PREF} EXCEPCION:", repr(e))
        traceback.print_exc()
    finally:
        try:
            limpieza()
            print(f"{PREF} LIMPIEZA SQL ejecutada.")
        except Exception as e2:
            print(f"{PREF} LIMPIEZA FALLO:", repr(e2))
    print()
    print("=" * 70)
    total = log_ok + log_fail
    print(f"RESUMEN ALARMAS: PASS {log_ok}/{total} FALLOS {log_fail}")
    print("=" * 70)
    sys.exit(0 if log_fail == 0 else 1)
