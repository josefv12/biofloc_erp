#!/usr/bin/env python3
"""
Script de pruebas oficiales — FASE 6 INVENTARIO CORE
Biofloc ERP V1

Ejecutar:
  1. Levantar servidor: uvicorn app.main:app --host 127.0.0.1 --port 8000
  2. python test_inventario.py

PRUEBAS (28):
  Bloque I  — Infraestructura + Autenticación / RBAC ( 1 -  5)
  Bloque II — Catálogo Categorías Inventario          ( 6 - 10)
  Bloque III — Catálogo Unidades                      (11 - 14)
  Bloque IV  — Catálogo Productos + Stock Vista       (15 - 20)
  Bloque V   — Tipos Movimiento Inventario            (21 - 22)
  Bloque VI  — Movimientos Inventario (INMUTABLES)    (23 - 28)
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Credenciales (siguen convención de test_mortalidades.py)
# ---------------------------------------------------------------------------
ADMIN_USER = "admin@biofloc.com"
ADMIN_PASS = "AdminBiofloc2026!"
TECNICO_USER = "tecnico_test@biofloc.com"
TECNICO_PASS = "Tecnico1234!"
OPERARIO_USER = "operario_test@biofloc.com"
OPERARIO_PASS = "Operario1234!"

# DB directa para validaciones profundas
DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")
DB_SCHEMA = "biofloc"

PREFIJO_TEST = "[TEST_INV]"

# IDs que se crearán durante el test (para limpieza final)
CREATED = {
    "categorias_ids": [],
    "unidades_ids": [],
    "productos_ids": [],
    "tipos_mov_ids": [],
    "movimientos_ids": [],
    "auditoria_ids_borrar": [],
}

PASS_ICON = "[OK]"
FAIL_ICON = "[FAIL]"
results = []


def log(num, name, ok, detail=""):
    icon = PASS_ICON if ok else FAIL_ICON
    num_str = str(num) if not isinstance(num, int) else f"{num:02d}"
    msg = f"  {icon} [{num_str}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    results.append((num, name, ok, detail))


def get_token(correo, password):
    r = requests.post(f"{BASE}/api/v1/auth/login",
                      json={"correo": correo, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def auth_header(token):
    return {**HEADERS_JSON, "Authorization": f"Bearer {token}"}


# =========================================================================
# BLOQUE I — Infraestructura + Autenticación / RBAC
# =========================================================================
def t01_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == "ok" and r.json().get("database") == "ok"
    log(1, "GET /health api+db ok", ok, str(r.json()))


def t02_login_admin():
    token = get_token(ADMIN_USER, ADMIN_PASS)
    ok = token is not None
    log(2, "Login ADMINISTRADOR ok", ok,
        f"token={'...'+token[-12:] if token else 'NONE'}")
    return token


def t03_login_tecnico():
    token = get_token(TECNICO_USER, TECNICO_PASS)
    ok = token is not None
    log(3, "Login TÉCNICO ok", ok,
        f"token={'...'+token[-12:] if token else 'NONE'}")
    return token


def t04_login_operario():
    token = get_token(OPERARIO_USER, OPERARIO_PASS)
    ok = token is not None
    log(4, "Login OPERARIO ok", ok,
        f"token={'...'+token[-12:] if token else 'NONE'}")
    return token


def t05_sin_jwt_403():
    r = requests.get(f"{BASE}/api/v1/categorias-inventario/")
    ok = r.status_code == 403
    log(5, "GET categorias-inventario sin JWT -> 403", ok, f"status={r.status_code}")


# =========================================================================
# BLOQUE II — Categorías Inventario (lectura 3 roles, escritura ADMIN+TEC)
# =========================================================================
def t06_lista_categorias_admin(admin_token):
    r = requests.get(f"{BASE}/api/v1/categorias-inventario/", headers=auth_header(admin_token))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 5
    log(6, "GET /categorias-inventario ADMIN -> 200 (>=5 semilla)", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


def t07_post_categoria_valida(admin_token):
    payload = {"nombre": f"{PREFIJO_TEST} CATEGORIA_A",
               "descripcion": "Categoría de prueba automatizada",
               "activo": True}
    r = requests.post(f"{BASE}/api/v1/categorias-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 201
    if ok:
        CREATED["categorias_ids"].append(r.json()["id"])
    log(7, "POST categoría válida ADMIN -> 201", ok,
        f"status={r.status_code} body={r.text[:120]}")
    return r.json()["id"] if ok else None


def t08_post_categoria_duplicada_409(admin_token):
    payload = {"nombre": f"{PREFIJO_TEST} CATEGORIA_A",
               "descripcion": "Duplicado intencional"}
    r = requests.post(f"{BASE}/api/v1/categorias-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 409
    log(8, "POST categoría nombre UNIQUE duplicado -> 409", ok,
        f"status={r.status_code}")


def t09_put_categoria(admin_token, cat_id):
    if not cat_id:
        log(9, "PUT categoría -> SKIP (cat_id None)", False)
        return
    payload = {"nombre": f"{PREFIJO_TEST} CATEGORIA_A_EDIT",
               "descripcion": "Editada en prueba",
               "activo": False}
    r = requests.put(f"{BASE}/api/v1/categorias-inventario/{cat_id}",
                     json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 200 and r.json().get("activo") is False
    log(9, "PUT categoría existente ADMIN -> 200 activo=False", ok,
        f"status={r.status_code} activo={r.json().get('activo') if r.status_code==200 else 'N/A'}")


def t10_categoria_escritura_operario_403(oper_token):
    """OPERARIO NO puede escribir catálogos según matriz RBAC."""
    payload = {"nombre": f"{PREFIJO_TEST} CAT_OPERARIO", "activo": True}
    r = requests.post(f"{BASE}/api/v1/categorias-inventario/",
                      json=payload, headers=auth_header(oper_token))
    ok = r.status_code == 403
    log(10, "POST categoría OPERARIO sin permiso escritura -> 403", ok,
        f"status={r.status_code}")


# =========================================================================
# BLOQUE III — Unidades
# =========================================================================
def t11_post_unidad_valida(tec_token):
    """TÉCNICO SÍ puede escribir catálogos (ADMIN+TEC)."""
    payload = {"nombre": f"{PREFIJO_TEST} Caja",
               "simbolo": f"cj{len(CREATED['unidades_ids'])}",
               "activo": True}
    r = requests.post(f"{BASE}/api/v1/unidades/",
                      json=payload, headers=auth_header(tec_token))
    ok = r.status_code == 201
    if ok:
        CREATED["unidades_ids"].append(r.json()["id"])
    log(11, "POST unidad válida TÉCNICO -> 201", ok,
        f"status={r.status_code} body={r.text[:120]}")


def t12_put_unidad(tec_token):
    if not CREATED["unidades_ids"]:
        log(12, "PUT unidad -> SKIP", False)
        return
    u_id = CREATED["unidades_ids"][0]
    payload = {"nombre": f"{PREFIJO_TEST} Caja Edit",
               "simbolo": f"cj{len(CREATED['unidades_ids'])}",
               "activo": True}
    r = requests.put(f"{BASE}/api/v1/unidades/{u_id}",
                     json=payload, headers=auth_header(tec_token))
    ok = r.status_code == 200 and "Edit" in r.json().get("nombre", "")
    log(12, "PUT unidad TÉCNICO -> 200 nombre actualizado", ok,
        f"status={r.status_code} nombre={r.json().get('nombre') if r.status_code==200 else 'N/A'}")


def t13_post_unidad_simbolo_duplicado_409(admin_token):
    """UNIQUE(simbolo). Usar el simbolo de una unidad semilla existente (kg)."""
    payload = {"nombre": f"{PREFIJO_TEST} Kilo2", "simbolo": "kg", "activo": True}
    r = requests.post(f"{BASE}/api/v1/unidades/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 409
    log(13, "POST unidad símbolo 'kg' UNIQUE duplicado -> 409", ok,
        f"status={r.status_code}")


def t14_lista_unidades_operario(oper_token):
    r = requests.get(f"{BASE}/api/v1/unidades/", headers=auth_header(oper_token))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 5
    log(14, "GET /unidades OPERARIO (lectura sí) -> 200", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


# =========================================================================
# BLOQUE IV — Productos + Stock Vista
# =========================================================================
def t15_post_producto_valido(admin_token):
    """Usa categoria_id=1 ALIMENTO, unidad_id=1 kg (semilla)."""
    cod = f"INV-TEST-{int(datetime.now().timestamp())}"
    payload = {
        "codigo": cod,
        "nombre": f"{PREFIJO_TEST} Harina 40%",
        "categoria_id": 1,
        "unidad_id": 1,
        "stock_minimo": 2.5,
        "activo": True,
    }
    r = requests.post(f"{BASE}/api/v1/productos/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 201
    p_id = None
    if ok:
        data = r.json()
        p_id = data["id"]
        CREATED["productos_ids"].append(p_id)
    log(15, f"POST producto válido codigo={cod} -> 201", ok,
        f"status={r.status_code} id={p_id}")
    return p_id


def t16_post_producto_codigo_duplicado_409(admin_token, producto_id):
    if not producto_id:
        log(16, "POST producto duplicado -> SKIP", False); return
    # Leer producto para reutilizar codigo
    r0 = requests.get(f"{BASE}/api/v1/productos/{producto_id}",
                      headers=auth_header(admin_token))
    cod = r0.json()["codigo"] if r0.status_code == 200 else "INV-NONE"
    payload = {"codigo": cod, "nombre": "Producto Duplicado",
               "categoria_id": 2, "unidad_id": 2, "stock_minimo": 0, "activo": True}
    r = requests.post(f"{BASE}/api/v1/productos/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 409
    log(16, f"POST producto codigo UNIQUE duplicado [{cod}] -> 409", ok,
        f"status={r.status_code}")


def t17_get_producto_id(admin_token, p_id):
    if not p_id:
        log(17, "GET producto/{id} -> SKIP", False); return
    r = requests.get(f"{BASE}/api/v1/productos/{p_id}", headers=auth_header(admin_token))
    ok = r.status_code == 200 and r.json().get("id") == p_id
    log(17, f"GET /productos/{p_id} -> 200 id correcto", ok,
        f"status={r.status_code} body={r.text[:120]}")


def t18_lista_productos_admin(admin_token):
    r = requests.get(f"{BASE}/api/v1/productos/", headers=auth_header(admin_token))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
    log(18, "GET /productos ADMIN -> 200 lista", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


def t19_vista_stock_global(admin_token):
    """GET /productos/stock apunta directo a biofloc.vista_stock_productos."""
    r = requests.get(f"{BASE}/api/v1/productos/stock", headers=auth_header(admin_token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    # Debe contener al menos el producto creado en T15 con stock 0 (porque entrada aún no hecha)
    log(19, "GET /productos/stock (vista) -> 200", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


def t20_stock_producto_individual(admin_token, p_id):
    if not p_id:
        log(20, "GET /productos/{id}/stock -> SKIP", False); return
    r = requests.get(f"{BASE}/api/v1/productos/{p_id}/stock", headers=auth_header(admin_token))
    ok = r.status_code == 200 and r.json().get("producto_id") == p_id
    log(20, f"GET /productos/{p_id}/stock (vista individual) -> 200", ok,
        f"status={r.status_code} stock={r.json().get('stock_actual') if r.status_code==200 else 'N/A'}")


# =========================================================================
# BLOQUE V — Tipos Movimiento Inventario
# =========================================================================
def t21_post_tipo_mov_valido(admin_token):
    payload = {"nombre": f"{PREFIJO_TEST} AJUSTE_POS",
               "descripcion": "Ajuste positivo inventario",
               "afecta_stock": 1}
    r = requests.post(f"{BASE}/api/v1/tipos-movimiento-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 201
    if ok:
        CREATED["tipos_mov_ids"].append(r.json()["id"])
    log(21, "POST tipo_mov válido afecta_stock=1 -> 201", ok,
        f"status={r.status_code} body={r.text[:120]}")


def t22_put_tipo_mov(admin_token):
    if not CREATED["tipos_mov_ids"]:
        log(22, "PUT tipo_mov -> SKIP", False); return
    t_id = CREATED["tipos_mov_ids"][0]
    payload = {"nombre": f"{PREFIJO_TEST} AJUSTE_POS_EDIT",
               "descripcion": "Editado por test",
               "afecta_stock": 1}
    r = requests.put(f"{BASE}/api/v1/tipos-movimiento-inventario/{t_id}",
                     json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 200 and "EDIT" in r.json().get("nombre", "")
    log(22, "PUT tipo_mov -> 200 nombre editado", ok,
        f"status={r.status_code} nombre={r.json().get('nombre') if r.status_code==200 else 'N/A'}")


# =========================================================================
# BLOQUE VI — Movimientos Inventario (INMUTABLES, Stock Negativo, Trazabilidad)
# =========================================================================
def t23_post_entrada_valida_operario(oper_token, p_id):
    """OPERARIO puede ESCRIBIR movimientos (3 roles sí). Tipo=1 ENTRADA (semilla)."""
    if not p_id:
        log(23, "POST movimiento ENTRADA -> SKIP", False); return None
    payload = {
        "producto_id": p_id,
        "tipo_movimiento_id": 1,
        "cantidad": 10.5,
        "referencia_tipo": "COMPRA_PRUEBA",
        "referencia_id": None,
        "observaciones": f"{PREFIJO_TEST} Entrada 10.5 kg Harina",
        "costo_unitario": 1.20,
        "costo_total": 12.60,
    }
    r = requests.post(f"{BASE}/api/v1/movimientos-inventario/",
                      json=payload, headers=auth_header(oper_token))
    ok = r.status_code == 201
    m_id = None
    if ok:
        m_id = r.json()["id"]
        CREATED["movimientos_ids"].append(m_id)
    log(23, "POST movimiento ENTRADA (OPERARIO ok) -> 201", ok,
        f"status={r.status_code} id={m_id} body={r.text[:120]}")
    return m_id


def t24_post_salida_stock_negativo_422(admin_token, p_id):
    """SALIDA > ENTRADA = stock insuficiente debe lanzar HTTP 422 en service layer.
    Hemos entrado 10.5; intentamos salida 50.0 (mayor) -> 422."""
    if not p_id:
        log(24, "POST salida stock negativo -> SKIP", False); return
    payload = {
        "producto_id": p_id,
        "tipo_movimiento_id": 2,
        "cantidad": 50.0,
        "observaciones": f"{PREFIJO_TEST} Intento salida excesiva",
    }
    r = requests.post(f"{BASE}/api/v1/movimientos-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 422
    log(24, "POST salida 50.0 > stock 10.5 -> 422 (regla servicio)", ok,
        f"status={r.status_code} detail={r.text[:180]}")


def t25_post_salida_igual_stock_ok(admin_token, p_id):
    """SALIDA == stock_actual (10.5) -> debe ser permitida (queda 0)."""
    if not p_id:
        log(25, "POST salida igual a stock -> SKIP", False); return
    payload = {
        "producto_id": p_id,
        "tipo_movimiento_id": 2,
        "cantidad": 10.5,
        "observaciones": f"{PREFIJO_TEST} Salida exacta = stock",
    }
    r = requests.post(f"{BASE}/api/v1/movimientos-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 201
    if ok:
        CREATED["movimientos_ids"].append(r.json()["id"])
    log(25, "POST salida exacta=stock 10.5 -> 201 permitida", ok,
        f"status={r.status_code} id={r.json().get('id') if ok else 'N/A'}")


def t26_post_referencia_aplicacion_biofloc_inexistente_404(admin_token, p_id):
    """Trazabilidad Biofloc: referencia_tipo='APLICACION_BIOFLOC' + referencia_id inexistente
    debe devolver 404 sin modificar AplicacionBiofloc."""
    if not p_id:
        log(26, "POST trazabilidad APLICACION_BIOFLOC 404 -> SKIP", False); return
    # Asegurar stock suficiente: hacemos una entrada adicional de 5 unds antes
    entrada = {
        "producto_id": p_id, "tipo_movimiento_id": 1,
        "cantidad": 5.0, "observaciones": f"{PREFIJO_TEST} Entrada trazabilidad"
    }
    re = requests.post(f"{BASE}/api/v1/movimientos-inventario/",
                       json=entrada, headers=auth_header(admin_token))
    if re.status_code == 201:
        CREATED["movimientos_ids"].append(re.json()["id"])
    # Ahora intentamos salida con referencia APLICACION_BIOFLOC inexistente
    payload = {
        "producto_id": p_id,
        "tipo_movimiento_id": 2,
        "cantidad": 1.0,
        "referencia_tipo": "APLICACION_BIOFLOC",
        "referencia_id": 999_999_999,
        "observaciones": f"{PREFIJO_TEST} Aplicación biofloc inexistente",
    }
    r = requests.post(f"{BASE}/api/v1/movimientos-inventario/",
                      json=payload, headers=auth_header(admin_token))
    ok = r.status_code == 404
    log(26, "POST salida referencia APLICACION_BIOFLOC=999M -> 404", ok,
        f"status={r.status_code} detail={r.text[:180]}")


def t27_get_movimiento_filtros(admin_token, p_id):
    """Listado con filtros AND: producto_id + fecha_desde/fecha_hasta.
    Rango UTC MUY amplio (-48h +24h) para cubrir diferencia Colombia UTC-5 y
    desfases de reloj; el filtrado por producto_id iguala al menos 1 registro."""
    if not p_id:
        log(27, "GET movimientos filtros -> SKIP", False); return
    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(hours=48)).isoformat()
    hasta = (ahora + timedelta(hours=24)).isoformat()
    params = {"producto_id": p_id, "fecha_desde": desde, "fecha_hasta": hasta}
    r = requests.get(f"{BASE}/api/v1/movimientos-inventario/",
                     params=params, headers=auth_header(admin_token))
    ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
    log(27, f"GET movimientos filtros producto_id={p_id} + fecha -> 200", ok,
        f"status={r.status_code} n={len(r.json()) if r.status_code==200 else 'N/A'}")


def t28_auditoria_postgres_insert_movimiento(p_id):
    """Validación DIRECTA EN PG: biofloc.auditoria tiene al menos 1 INSERT para la tabla
    movimientos_inventario durante ejecución de este test, con accion='INSERT'."""
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, tabla, accion
            FROM {DB_SCHEMA}.auditoria
            WHERE tabla = 'movimientos_inventario'
              AND accion = 'INSERT'
              AND (detalle->>'observaciones') LIKE %s
            ORDER BY id DESC
            LIMIT 1;
            """,
            (f"{PREFIJO_TEST}%",)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None
        if ok:
            CREATED["auditoria_ids_borrar"].append(row[0])
        log(28, "Auditoría PG INSERT movimientos_inventario PREFIJO_TEST", ok,
            f"auditoria_id={row[0] if row else 'NONE'} tabla={row[1] if row else '-'} accion={row[2] if row else '-'}")
    except Exception as e:
        log(28, "Auditoría PG INSERT movimientos_inventario -> EXCEPCIÓN", False, str(e))


# =========================================================================
# LIMPIEZA FINAL — Borrar registros creados con prefijo TEST para no contaminar
# =========================================================================
def limpieza():
    print("\n  --- LIMPIEZA DE DATOS DE PRUEBA ---")
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        # 1) Auditoría
        if CREATED["auditoria_ids_borrar"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.auditoria WHERE id = ANY(%s)",
                (CREATED["auditoria_ids_borrar"],)
            )
            print(f"  -> Auditoría: {cur.rowcount} rows eliminados")
        # Auditoría general por prefijo detalle:
        cur.execute(
            f"""
            DELETE FROM {DB_SCHEMA}.auditoria
            WHERE (detalle->>'nombre') LIKE %s
               OR (detalle->>'observaciones') LIKE %s
               OR (detalle->>'codigo') LIKE %s
               OR (detalle->>'simbolo') LIKE %s
            """,
            (f"{PREFIJO_TEST}%", f"{PREFIJO_TEST}%", "INV-TEST-%", "cj%")
        )
        print(f"  -> Auditoría (prefijo): {cur.rowcount} rows adicionales")

        # 2) Movimientos inventario
        if CREATED["movimientos_ids"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.movimientos_inventario WHERE id = ANY(%s)",
                (CREATED["movimientos_ids"],)
            )
            print(f"  -> Movimientos: {cur.rowcount} rows")

        # 3) Productos creados
        if CREATED["productos_ids"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.productos WHERE id = ANY(%s)",
                (CREATED["productos_ids"],)
            )
            print(f"  -> Productos: {cur.rowcount} rows")

        # 4) Tipos movimiento creados
        if CREATED["tipos_mov_ids"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.tipos_movimiento_inventario WHERE id = ANY(%s)",
                (CREATED["tipos_mov_ids"],)
            )
            print(f"  -> Tipos Mov: {cur.rowcount} rows")

        # 5) Unidades creadas
        if CREATED["unidades_ids"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.unidades WHERE id = ANY(%s)",
                (CREATED["unidades_ids"],)
            )
            print(f"  -> Unidades: {cur.rowcount} rows")

        # 6) Categorías creadas
        if CREATED["categorias_ids"]:
            cur.execute(
                f"DELETE FROM {DB_SCHEMA}.categorias_inventario WHERE id = ANY(%s)",
                (CREATED["categorias_ids"],)
            )
            print(f"  -> Categorias: {cur.rowcount} rows")

        # Fallback global por prefijo para cubrir cualquier edge-case
        cur.execute(f"DELETE FROM {DB_SCHEMA}.movimientos_inventario WHERE observaciones LIKE %s",
                    (f"{PREFIJO_TEST}%",))
        cur.execute(f"DELETE FROM {DB_SCHEMA}.productos WHERE nombre LIKE %s OR codigo LIKE %s",
                    (f"{PREFIJO_TEST}%", "INV-TEST-%"))
        cur.execute(f"DELETE FROM {DB_SCHEMA}.tipos_movimiento_inventario WHERE nombre LIKE %s",
                    (f"{PREFIJO_TEST}%",))
        cur.execute(f"DELETE FROM {DB_SCHEMA}.unidades WHERE nombre LIKE %s",
                    (f"{PREFIJO_TEST}%",))
        cur.execute(f"DELETE FROM {DB_SCHEMA}.categorias_inventario WHERE nombre LIKE %s",
                    (f"{PREFIJO_TEST}%",))

        conn.commit()
        cur.close()
        conn.close()
        print("  -> Limpieza completada (COMMIT)")
    except Exception as e:
        print(f"  [ERROR] Falló limpieza: {e}")


# =========================================================================
# EJECUTOR PRINCIPAL
# =========================================================================
def main():
    print("=" * 78)
    print(" BIOFLOC ERP V1 — PRUEBAS OFICIALES FASE 6 INVENTARIO CORE (28)")
    print("=" * 78)
    print()

    # --- Bloque I ---
    print("  [ Bloque I — Infraestructura + Autenticación / RBAC ]")
    t01_health()
    admin_tok = t02_login_admin()
    tec_tok = t03_login_tecnico()
    oper_tok = t04_login_operario()
    t05_sin_jwt_403()
    print()

    # --- Bloque II Categorías ---
    print("  [ Bloque II — Categorías Inventario ]")
    t06_lista_categorias_admin(admin_tok)
    cat_a = t07_post_categoria_valida(admin_tok)
    t08_post_categoria_duplicada_409(admin_tok)
    t09_put_categoria(admin_tok, cat_a)
    t10_categoria_escritura_operario_403(oper_tok)
    print()

    # --- Bloque III Unidades ---
    print("  [ Bloque III — Unidades ]")
    t11_post_unidad_valida(tec_tok)
    t12_put_unidad(tec_tok)
    t13_post_unidad_simbolo_duplicado_409(admin_tok)
    t14_lista_unidades_operario(oper_tok)
    print()

    # --- Bloque IV Productos ---
    print("  [ Bloque IV — Productos + Vista Stock ]")
    p_id = t15_post_producto_valido(admin_tok)
    t16_post_producto_codigo_duplicado_409(admin_tok, p_id)
    t17_get_producto_id(admin_tok, p_id)
    t18_lista_productos_admin(admin_tok)
    t19_vista_stock_global(admin_tok)
    t20_stock_producto_individual(admin_tok, p_id)
    print()

    # --- Bloque V Tipos Mov ---
    print("  [ Bloque V — Tipos Movimiento Inventario ]")
    t21_post_tipo_mov_valido(admin_tok)
    t22_put_tipo_mov(admin_tok)
    print()

    # --- Bloque VI Movimientos ---
    print("  [ Bloque VI — Movimientos Inventario (INMUTABLES) ]")
    t23_post_entrada_valida_operario(oper_tok, p_id)
    t24_post_salida_stock_negativo_422(admin_tok, p_id)
    t25_post_salida_igual_stock_ok(admin_tok, p_id)
    t26_post_referencia_aplicacion_biofloc_inexistente_404(admin_tok, p_id)
    t27_get_movimiento_filtros(admin_tok, p_id)
    t28_auditoria_postgres_insert_movimiento(p_id)
    print()

    # --- Resumen ---
    total = len(results)
    ok_count = sum(1 for _, _, x, _ in results if x)
    fail_count = total - ok_count

    print("=" * 78)
    print(f"  RESUMEN: {ok_count}/{total} APROBADAS  |  {fail_count} FALLOS")
    print("=" * 78)
    if fail_count:
        print("\n  DETALLE FALLOS:")
        for n, name, ok, det in results:
            if not ok:
                print(f"    - [{n:02d}] {name}  :: {det}")

    # Siempre limpiar incluso si hay fallos (mejor esfuerzo)
    print()
    limpieza()

    print()
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
