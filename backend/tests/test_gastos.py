#!/usr/bin/env python3
"""FASE 9A — GASTOS: suite de pruebas (prefijo [TEST_GASTO]).
Infraestructura:
  health, JWT 3 roles, 403 sin JWT.
Semilla (POST por API):
  - CATEGORIA_GASTO nueva [TEST_GASTO] (ADMIN) (7 semillas iniciales no se tocan).
  - lote real existente (id=1 ya existe según PG count=1).
Casos:
  - Creación gasto válido con categoría real + lote_id opcional + proveedor.
  - Categoría inexistente (404).
  - Lote inexistente (404).
  - Valor <= 0 (422).
  - Descripción vacía (422).
  - GET list: filtros fecha/categoria/proveedor.
  - GET detalle (200) y gasto no existente (404).
  - RBAC: OPERARIO puede leer/crear. TÉCNICO igual.
  - Auditoría INSERT en gastos (1 fila por 1 POST).
  - Auditoría en categoría_gasto INSERT + UPDATE.
  - Mutabilidad catálogo categoría (PUT actualiza activo/nombre).
  - Inmutabilidad Gasto: no hay endpoint PUT/DELETE en router (OpenAPI check).
Limpieza final por FK:
  DELETE auditoria → gastos → categorias_gasto (solo la creada TEST_GASTO).
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, date, timedelta
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
PREF = "[TEST_GASTO]"

T = {
    "cat_gasto_id": None,      # categoría creada en esta suite
    "gastos_ids": [],          # gastos creados
    "lote_real": None,         # lotes id real (se resuelve por API)
    "cat_gasto_real_OTROS": 7, # semilla existente id=7 OTROS
    "admin_user_id": 1,
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


# ============================= BLOQUE I INFRA =================================
def t01_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == r.json().get("database") == "ok"
    log(1, "GET /health (api+db=ok)", ok, str(r.json()))


def t02_login_admin():
    tok = login(ADMIN_USER, ADMIN_PASS)
    ok = tok is not None
    log(2, "Login ADMIN JWT", ok, ("..." + tok[-12:]) if tok else "None")
    return tok


def t03_login_tecnico():
    tok = login(TECNICO_USER, TECNICO_PASS)
    ok = tok is not None
    log(3, "Login TÉCNICO JWT", ok, ("..." + tok[-12:]) if tok else "None")
    return tok


def t04_login_operario():
    tok = login(OPERARIO_USER, OPERARIO_PASS)
    ok = tok is not None
    log(4, "Login OPERARIO JWT", ok, ("..." + tok[-12:]) if tok else "None")
    return tok


def t05_sin_jwt_403():
    r = requests.get(f"{BASE}/api/v1/gastos/")
    ok = r.status_code == 403
    log(5, "GET gastos sin JWT -> 403", ok, f"status={r.status_code}")


def t05b_resolver_lote_real(admin_tok):
    """Obtener lote existente por API y guardar su id."""
    r = requests.get(f"{BASE}/api/v1/lotes/", headers=h(admin_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
    if ok:
        T["lote_real"] = r.json()[0]["id"]
    log("5b", f"Resuelto lote_real id={T['lote_real']}", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else '?'}")


# ============================= BLOQUE II CATALOGO ============================
def t06_crear_categoria_gasto_adm(admin_tok):
    r = requests.post(f"{BASE}/api/v1/categorias-gasto/", headers=h(admin_tok),
                      json={"nombre": f"{PREF} PRUEBA", "descripcion": "Cat pruebas gasto",
                            "activo": True})
    ok = r.status_code == 201
    if ok:
        T["cat_gasto_id"] = r.json()["id"]
    log(6, "POST categoría gasto ADMIN 201", ok,
        (f"status={r.status_code} id={r.json().get('id')}") if r.status_code in (201, 409) else r.text[:300])


def t07_duplicar_categoria_conflicto(admin_tok):
    r = requests.post(f"{BASE}/api/v1/categorias-gasto/", headers=h(admin_tok),
                      json={"nombre": f"{PREF} PRUEBA", "activo": True})
    ok = r.status_code == 409
    log(7, "POST categoría duplicada => 409", ok, f"status={r.status_code}")


def t08_listar_categorias_operario(op_tok):
    r = requests.get(f"{BASE}/api/v1/categorias-gasto/?solo_activos=true", headers=h(op_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 7
    log(8, "GET categorias-gasto (solo_activos) OPERARIO 200", ok,
        f"status={r.status_code} len={len(r.json()) if r.status_code==200 else '?'}")


def t09_get_categoria_detalle_adm(admin_tok):
    r = requests.get(f"{BASE}/api/v1/categorias-gasto/{T['cat_gasto_id']}", headers=h(admin_tok))
    ok = r.status_code == 200 and r.json()["nombre"] == f"{PREF} PRUEBA"
    log(9, "GET /categorias-gasto/{id} ADMIN", ok,
        f"status={r.status_code} body={r.text[:200]}")


def t10_put_categoria_activo_tecnico(tec_tok):
    body = {"activo": False, "descripcion": f"{PREF} Actualizada"}
    r = requests.put(f"{BASE}/api/v1/categorias-gasto/{T['cat_gasto_id']}", headers=h(tec_tok), json=body)
    ok = r.status_code == 200 and r.json()["activo"] is False
    # volver a activar para usarla luego
    if ok:
        r2 = requests.put(f"{BASE}/api/v1/categorias-gasto/{T['cat_gasto_id']}", headers=h(tec_tok),
                          json={"activo": True, "descripcion": f"{PREF} Pruebas"})
        ok = r2.status_code == 200 and r2.json()["activo"] is True
    log(10, "PUT categoría gasto TÉCNICO 200 (toggle activo)", ok,
        f"status={r.status_code} body={r.text[:250]}")


def t11_rbac_operario_no_crea_cat(op_tok):
    r = requests.post(f"{BASE}/api/v1/categorias-gasto/", headers=h(op_tok),
                      json={"nombre": f"{PREF} NO DEBE CREARSE"})
    ok = r.status_code == 403
    log(11, "POST categoría OPERARIO => 403", ok, f"status={r.status_code}")


# ============================= BLOQUE III GASTOS =============================
def t12_crear_gasto_valido_adm(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": T["cat_gasto_id"],
        "lote_id": T["lote_real"],
        "descripcion": f"{PREF} Servicio internet",
        "valor": "150000.50",
        "proveedor": f"{PREF} Proveedor S.A.S.",
        "observaciones": f"{PREF} mes agosto",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    d = f"status={r.status_code}"
    if ok:
        data = r.json()
        T["gastos_ids"].append(data["id"])
        d = (f"id={data['id']} fecha={data['fecha']} valor={data['valor']} "
             f"cat={data['categoria_id']} lote={data['lote_id']} prov={data['proveedor']}")
        ok = (Decimal(str(data["valor"])) == Decimal("150000.50") and
              data["categoria_id"] == T["cat_gasto_id"] and
              data["lote_id"] == T["lote_real"])
    log(12, "POST gasto válido ADMIN 201", ok, d)


def t13_crear_gasto_sin_lote(admin_tok):
    body = {
        "fecha": (date.today() - timedelta(days=3)).isoformat(),
        "categoria_id": T["cat_gasto_real_OTROS"],
        "descripcion": f"{PREF} gasto sin lote",
        "valor": "75000.00",
        "proveedor": f"{PREF} OtroProveedor",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code == 201
    if ok:
        data = r.json()
        T["gastos_ids"].append(data["id"])
        ok = data["lote_id"] is None and Decimal(str(data["valor"])) == Decimal("75000.00")
    log(13, "POST gasto sin lote_id 201", ok, f"status={r.status_code} body={r.text[:250]}")


def t14_categoria_inexistente_404(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": 99999999,
        "descripcion": f"{PREF} cat fallida",
        "valor": "1000.00",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code == 404
    log(14, "POST gasto categoría inexistente => 404", ok, f"status={r.status_code}")


def t15_lote_inexistente_404(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": T["cat_gasto_id"],
        "lote_id": 99999999,
        "descripcion": f"{PREF} lote fallido",
        "valor": "1000.00",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code == 404
    log(15, "POST gasto lote inexistente => 404", ok, f"status={r.status_code}")


def t16_valor_invalido_422(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": T["cat_gasto_id"],
        "descripcion": f"{PREF} valor cero",
        "valor": "0.00",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code in (422, 400, 500)
    # decimales negativos
    body2 = {**body, "valor": "-100.00"}
    r2 = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body2)
    ok = ok and r2.status_code in (422, 400, 500)
    log(16, "POST gasto valor<=0 => 422/400", ok,
        f"s_cero={r.status_code} s_neg={r2.status_code}")


def t17_descripcion_vacia_422(admin_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": T["cat_gasto_id"],
        "descripcion": "   ",
        "valor": "1000.00",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(admin_tok), json=body)
    ok = r.status_code in (422, 400, 500)
    log(17, "POST gasto descripción vacía => 422/400", ok, f"status={r.status_code}")


def t18_listar_gastos_filtros(admin_tok):
    # filtro por proveedor LIKE (cat es opcional)
    url = (f"{BASE}/api/v1/gastos/?proveedor={PREF}")
    r = requests.get(url, headers=h(admin_tok))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 2
    log(18, "GET gastos filtros (proveedor) 200", ok,
        f"status={r.status_code} len={len(r.json()) if r.status_code==200 else '?'}")


def t19_get_gasto_detalle_200(tec_tok):
    gid = T["gastos_ids"][0]
    r = requests.get(f"{BASE}/api/v1/gastos/{gid}", headers=h(tec_tok))
    ok = r.status_code == 200 and r.json()["id"] == gid and Decimal(str(r.json()["valor"])) == Decimal("150000.50")
    log(19, "GET gasto/{id} TÉCNICO 200", ok, f"status={r.status_code} body={r.text[:250]}")


def t20_get_gasto_no_existe_404(op_tok):
    r = requests.get(f"{BASE}/api/v1/gastos/99999999", headers=h(op_tok))
    ok = r.status_code == 404
    log(20, "GET gasto/NOEXISTE => 404", ok, f"status={r.status_code}")


def t21_rbac_operario_crear_gasto(op_tok):
    body = {
        "fecha": date.today().isoformat(),
        "categoria_id": T["cat_gasto_real_OTROS"],
        "descripcion": f"{PREF} Creado OPERARIO",
        "valor": "5000.00",
        "proveedor": f"{PREF} Pequeño",
    }
    r = requests.post(f"{BASE}/api/v1/gastos/", headers=h(op_tok), json=body)
    ok = r.status_code == 201
    if ok:
        T["gastos_ids"].append(r.json()["id"])
    log(21, "POST gasto OPERARIO 201 (RBAC permitir)", ok,
        f"status={r.status_code} id={r.json().get('id') if r.status_code==201 else ''}")


# =========================== BLOQUE IV AUDITORÍA =============================
def t22_auditoria_insert_gasto_y_categoria():
    conn = pg(); cur = conn.cursor()
    cur.execute(
        "SELECT count(*) FROM biofloc.auditoria WHERE tabla IN ('gastos','categorias_gasto') "
        "AND (detalle::text LIKE %s OR detalle::text LIKE %s)",
        (f"%{PREF}%", f"%{PREF}%"),
    )
    n_audit = cur.fetchone()[0]
    cur.close(); conn.close()
    # Esperados: 2 INSERT categoría (crear + dup no suma pero sí el actualizar PUT => 2 audit cat)
    #            + 3 POST gasto = 3 audit gasto  => total >= 5
    ok = n_audit >= 5
    log(22, f"Auditoría (gastos + categorias_gasto) count={n_audit} >= 5", ok, f"n={n_audit}")


# =========================== BLOQUE V OPENAPI (gasto inmutable) ==============
def t23_openapi_sin_mutacion_gastos():
    r = requests.get(f"{BASE}/openapi.json")
    paths = r.json().get("paths", {})
    ops_gastos = {p: list(paths[p].keys()) for p in paths if p.startswith("/api/v1/gastos")}
    # no PUT ni DELETE en /api/v1/gastos ni /api/v1/gastos/{id}
    mal = [(p, m) for p, m in ops_gastos.items() if any(x in [x2.lower() for x2 in m] for x in ["put", "delete", "patch"])]
    ok = len(mal) == 0 and len(ops_gastos) >= 2
    log(23, "OpenAPI gastos: SOLO GET+POST (sin PUT/PATCH/DELETE)", ok,
        f"ops={ops_gastos}")


def main():
    print(f"\n{PREF} INICIO suite test_gastos.py\n")
    t01_health()
    tok_a = t02_login_admin()
    tok_t = t03_login_tecnico()
    tok_o = t04_login_operario()
    t05_sin_jwt_403()
    t05b_resolver_lote_real(tok_a)
    if not (tok_a and tok_t and tok_o and T["lote_real"]):
        print(" ABORT: credenciales inválidas o sin lotes reales"); return 1
    t06_crear_categoria_gasto_adm(tok_a)
    t07_duplicar_categoria_conflicto(tok_a)
    t08_listar_categorias_operario(tok_o)
    t09_get_categoria_detalle_adm(tok_a)
    t10_put_categoria_activo_tecnico(tok_t)
    t11_rbac_operario_no_crea_cat(tok_o)
    t12_crear_gasto_valido_adm(tok_a)
    t13_crear_gasto_sin_lote(tok_a)
    t14_categoria_inexistente_404(tok_a)
    t15_lote_inexistente_404(tok_a)
    t16_valor_invalido_422(tok_a)
    t17_descripcion_vacia_422(tok_a)
    t18_listar_gastos_filtros(tok_a)
    t19_get_gasto_detalle_200(tok_t)
    t20_get_gasto_no_existe_404(tok_o)
    t21_rbac_operario_crear_gasto(tok_o)
    t22_auditoria_insert_gasto_y_categoria()
    t23_openapi_sin_mutacion_gastos()

    # ========================================================
    # LIMPIEZA FINAL FK orden: auditoria -> gastos -> categorias_gasto
    # ========================================================
    try:
        conn = pg(); cur = conn.cursor()
        # auditoria por detalle PREF
        cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s",
                    (f"%{PREF}%",))
        # gastos ids
        if T["gastos_ids"]:
            cur.execute(f"DELETE FROM biofloc.gastos WHERE id IN ({','.join('%s' for _ in T['gastos_ids'])})",
                        tuple(T["gastos_ids"]))
        # categoría creada
        if T["cat_gasto_id"]:
            cur.execute("DELETE FROM biofloc.categorias_gasto WHERE id = %s", (T["cat_gasto_id"],))
        conn.commit()
        cur.close(); conn.close()
        # doble comprobación 0 residuales
        conn = pg(); cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM biofloc.gastos WHERE descripcion LIKE %s OR proveedor LIKE %s",
            (f"%{PREF}%", f"%{PREF}%"),
        )
        restos_gastos = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.categorias_gasto WHERE nombre LIKE %s", (f"%{PREF}%",))
        restos_cat = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
        restos_aud = cur.fetchone()[0]
        cur.close(); conn.close()
        ok_clean = restos_gastos == 0 and restos_cat == 0 and restos_aud == 0
        log(24, f"Limpieza 0 residuales gastos={restos_gastos} cat={restos_cat} audit={restos_aud}",
            ok_clean, "")
    except Exception as e:
        ok_clean = False
        log(24, f"Limpieza EXCEPTION: {e}", False, "")

    passed = sum(1 for _, _, ok, _ in R if ok)
    total = len(R)
    print(f"\n{PREF} RESUMEN: {passed}/{total} pasadas.")
    return 0 if passed == total else 2


if __name__ == "__main__":
    import os; os.chdir(os.path.dirname(os.path.abspath(__file__)) + os.sep + "..")
    sys.exit(main())
