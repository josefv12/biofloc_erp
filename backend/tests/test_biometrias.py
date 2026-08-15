#!/usr/bin/env python3
"""
Script de pruebas reales para el bloque Biometrías — Biofloc ERP V1
Ejecutar: python test_biometrias.py

Pruebas:
 1. Login real + JWT
 2. POST biometría válida
 3. GET biometría por ID
 4. GET listado
 5. GET listado filtrado por lote_id
 6. Asociación correcta con lote
 7. Datos inválidos (cantidad=0, peso negativo)
 8. Lote inexistente
 9. Acceso sin JWT
10. Rol sin permiso (OPERARIO no puede POST)
11. Auditoría en PostgreSQL
12. Validación de PostgreSQL (no se crearon tablas extra)
13. GET /health
"""
import sys
import json
import requests
import psycopg2
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Credenciales de prueba — ajustar si los datos de la BD son distintos
# ---------------------------------------------------------------------------
ADMIN_USER = "admin@biofloc.com"
ADMIN_PASS = "AdminBiofloc2026!"
TECNICO_USER = "tecnico_test@biofloc.com"
TECNICO_PASS = "Tecnico1234!"
OPERARIO_USER = "operario_test@biofloc.com"
OPERARIO_PASS = "Operario1234!"

# DB directa para validaciones
DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")
DB_SCHEMA = "biofloc"

# IDs de prueba — se establecen dinámicamente durante la ejecucion
TEST_BIOMETRIA_IDS = []

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
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": correo, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# PRE-REQUISITO: obtener un lote_id valido de la BD
# ---------------------------------------------------------------------------
def obtener_lote_valido():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT id, fecha_siembra FROM biofloc.lotes LIMIT 1;")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row  # (id, fecha_siembra)
    except Exception as e:
        print(f"  [WARN] No se pudo conectar a PostgreSQL: {e}")
        return None


# ---------------------------------------------------------------------------
# PRUEBA 13: GET /health
# ---------------------------------------------------------------------------
def test_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == "ok"
    log(13, "GET /health", ok, str(r.json()))


# ---------------------------------------------------------------------------
# PRUEBA 1: Login + JWT
# ---------------------------------------------------------------------------
def test_login():
    token = get_token(ADMIN_USER, ADMIN_PASS)
    ok = token is not None
    log(1, f"Login ADMINISTRADOR ({ADMIN_USER})", ok, f"token={'...'+token[-12:] if token else 'NONE'}")
    return token


# ---------------------------------------------------------------------------
# PRUEBA 9: Acceso sin JWT
# ---------------------------------------------------------------------------
def test_sin_jwt():
    r = requests.get(f"{BASE}/api/v1/biometrias/")
    ok = r.status_code == 403  # HTTPBearer devuelve 403 sin credentials
    log(9, "GET /biometrias sin JWT → 403", ok, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# PRUEBA 7a: Datos invalidos — cantidad_muestra = 0
# ---------------------------------------------------------------------------
def test_datos_invalidos_cantidad(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_muestra": 0,
        "peso_total_muestra": 10.0
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(7, "POST biometria con cantidad_muestra=0 → 422", ok, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# PRUEBA 7b: Datos invalidos — peso negativo
# ---------------------------------------------------------------------------
def test_datos_invalidos_peso(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_muestra": 10,
        "peso_total_muestra": -5.0
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log("7b", "POST biometria con peso_total_muestra=-5 -> 422", ok, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# PRUEBA 8: Lote inexistente
# ---------------------------------------------------------------------------
def test_lote_inexistente(token):
    payload = {
        "lote_id": 999999,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_muestra": 10,
        "peso_total_muestra": 5.0
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload, headers=auth_header(token))
    ok = r.status_code == 404
    log(8, "POST biometria con lote_id=999999 → 404", ok, f"status={r.status_code} | {r.text[:80]}")


# ---------------------------------------------------------------------------
# PRUEBA 2: POST biometria valida
# ---------------------------------------------------------------------------
def test_crear_biometria(token, lote_id, fecha_siembra):
    # fecha_hora debe ser >= fecha_siembra
    fecha_hora = datetime.now(timezone.utc).isoformat()
    payload = {
        "lote_id": lote_id,
        "fecha_hora": fecha_hora,
        "cantidad_muestra": 30,
        "peso_total_muestra": 450.750,
        "observaciones": "[TEST_BIOMETRIA] Muestreo automatizado de prueba",
        "talla_promedio": 12.5,
        "unidad_talla": "cm"
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload, headers=auth_header(token))
    ok = r.status_code == 201
    bm_id = None
    if ok:
        data = r.json()
        bm_id = data["id"]
        TEST_BIOMETRIA_IDS.append(bm_id)
        detail = f"id={bm_id} lote_id={data['lote_id']} peso={data['peso_total_muestra']}"
    else:
        detail = f"status={r.status_code} | {r.text[:120]}"
    log(2, "POST biometria valida → 201", ok, detail)
    return bm_id


# ---------------------------------------------------------------------------
# PRUEBA 3: GET biometria por ID
# ---------------------------------------------------------------------------
def test_get_by_id(token, bm_id):
    r = requests.get(f"{BASE}/api/v1/biometrias/{bm_id}", headers=auth_header(token))
    ok = r.status_code == 200
    if ok:
        data = r.json()
        detail = f"id={data['id']} lote_id={data['lote_id']} created_at={data['created_at']}"
    else:
        detail = f"status={r.status_code} | {r.text[:80]}"
    log(3, f"GET /biometrias/{bm_id}", ok, detail)


# ---------------------------------------------------------------------------
# PRUEBA 4: GET listado
# ---------------------------------------------------------------------------
def test_listar(token):
    r = requests.get(f"{BASE}/api/v1/biometrias/", headers=auth_header(token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    log(4, "GET /biometrias/ (listado completo)", ok, f"registros={len(r.json()) if ok else 'ERROR'}")


# ---------------------------------------------------------------------------
# PRUEBA 5: GET listado filtrado por lote_id
# ---------------------------------------------------------------------------
def test_listar_filtrado(token, lote_id):
    r = requests.get(f"{BASE}/api/v1/biometrias/?lote_id={lote_id}", headers=auth_header(token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    if ok:
        todos_del_lote = all(b["lote_id"] == lote_id for b in r.json())
        ok = ok and todos_del_lote
        detail = f"registros={len(r.json())} todos_lote_id_correcto={todos_del_lote}"
    else:
        detail = f"status={r.status_code}"
    log(5, f"GET /biometrias/?lote_id={lote_id} (filtrado)", ok, detail)


# ---------------------------------------------------------------------------
# PRUEBA 6: Asociacion correcta con lote (verificar en BD)
# ---------------------------------------------------------------------------
def test_asociacion_lote(bm_id, lote_id):
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            "SELECT lote_id FROM biofloc.biometrias WHERE id = %s;", (bm_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None and row[0] == lote_id
        detail = f"BD: biometrias.lote_id={row[0] if row else 'NULL'} esperado={lote_id}"
    except Exception as e:
        ok = False
        detail = str(e)
    log(6, "Asociacion biometria↔lote en PostgreSQL", ok, detail)


# ---------------------------------------------------------------------------
# PRUEBA 10: Rol sin permiso (OPERARIO intenta POST)
# ---------------------------------------------------------------------------
def test_rol_sin_permiso(lote_id):
    token = get_token(OPERARIO_USER, OPERARIO_PASS)
    if not token:
        log(10, "Rol OPERARIO POST → 403", False, "No se pudo obtener token OPERARIO")
        return
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_muestra": 10,
        "peso_total_muestra": 100.0
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload, headers=auth_header(token))
    ok = r.status_code == 403
    log(10, "Rol OPERARIO POST /biometrias → 403", ok, f"status={r.status_code} | {r.text[:80]}")


# ---------------------------------------------------------------------------
# PRUEBA 11: Auditoria en PostgreSQL
# ---------------------------------------------------------------------------
def test_auditoria(bm_id):
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, accion, tabla, registro_id FROM biofloc.auditoria "
            "WHERE tabla = 'biometrias' AND registro_id = %s ORDER BY id DESC LIMIT 1;",
            (bm_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None and row[1] == "INSERT" and row[2] == "biometrias"
        detail = f"auditoria.id={row[0]} accion={row[1]} tabla={row[2]} registro_id={row[3]}" if row else "SIN REGISTRO"
    except Exception as e:
        ok = False
        detail = str(e)
    log(11, "Auditoria INSERT en biofloc.auditoria", ok, detail)


# ---------------------------------------------------------------------------
# PRUEBA 12: Validacion PostgreSQL — no se crearon tablas
# ---------------------------------------------------------------------------
def test_postgresql_integridad():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'biofloc'
            ORDER BY table_name;
        """)
        tablas = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        # Solo debe tener las tablas definidas en el schema original
        tablas_esperadas = {
            "alimentaciones", "aplicaciones_biofloc", "auditoria",
            "biometrias", "categorias_insumos", "cosechas",
            "equipos_estanques", "equipos", "especies", "estados_estanque",
            "estados_lote", "estanques", "etapas_productivas",
            "inventario_insumos", "lotes", "mediciones_agua",
            "mortalidades", "movimientos_inventario", "parametros_agua",
            "productos_alimentacion", "roles", "tipos_equipo",
            "tipos_estanque", "unidades_medida", "usuarios",
            "vista_biomasa_lotes", "tipos_mantenimiento", "alarmas", "ventas",
            "vista_ultima_biometria", "categorias_inventario", "detalles_venta",
            "vista_supervivencia_lotes", "tipos_movimiento_inventario", "mantenimientos",
            "unidades", "vista_stock_productos", "categorias_gasto", "referencias_produccion",
            "detalles_compra", "gastos", "referencias_agua", "tipos_aplicacion_biofloc",
            "estados_equipo", "compras", "mediciones_biofloc", "niveles_alarma",
            "tipos_alarma", "eventos_energia", "estados_alarma", "productos", "fallas"
        }
        extra = set(tablas) - tablas_esperadas
        ok = len(extra) == 0
        detail = (
            f"tablas en BD={len(tablas)} | extras={extra if extra else 'ninguna'}"
        )
    except Exception as e:
        ok = False
        detail = str(e)
    log(12, "PostgreSQL: no se crearon tablas extra", ok, detail)


# ---------------------------------------------------------------------------
# LIMPIEZA: eliminar unicamente los registros de prueba
# ---------------------------------------------------------------------------
def limpiar_datos_prueba():
    if not TEST_BIOMETRIA_IDS:
        print("\n  [INFO] No hay registros de prueba para eliminar.")
        return
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        # Eliminar primero los registros de auditoria asociados
        cur.execute(
            "DELETE FROM biofloc.auditoria WHERE tabla = 'biometrias' AND registro_id = ANY(%s);",
            (TEST_BIOMETRIA_IDS,)
        )
        # Eliminar las biometrias de prueba
        cur.execute(
            "DELETE FROM biofloc.biometrias WHERE id = ANY(%s);",
            (TEST_BIOMETRIA_IDS,)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"\n  [CLEAN] Limpieza: eliminadas {len(TEST_BIOMETRIA_IDS)} biometria(s) de prueba: {TEST_BIOMETRIA_IDS}")
    except Exception as e:
        print(f"  [WARN] Error durante limpieza: {e}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("\n" + "="*60)
    print("  BIOFLOC ERP V1 - Pruebas Biometrias")
    print("="*60)

    # Verificar que el servidor esté levantado
    try:
        requests.get(f"{BASE}/health", timeout=3)
    except Exception:
        print(f"\n  [ERROR] El servidor no esta corriendo en {BASE}")
        print("     Iniciar con: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)

    # Obtener lote de la BD
    lote_row = obtener_lote_valido()
    if not lote_row:
        print("\n  [ERROR] No se pudo obtener un lote valido de la BD. Verificar conexion.")
        sys.exit(1)
    lote_id, fecha_siembra = lote_row
    print(f"\n  [INFO] Usando lote_id={lote_id} (fecha_siembra={fecha_siembra})\n")

    # Ejecutar pruebas
    test_health()                                  # 13
    token = test_login()                           # 1
    if not token:
        print("\n  [ERROR] Login fallo. Verificar credenciales en el script.")
        sys.exit(1)

    test_sin_jwt()                                 # 9
    test_datos_invalidos_cantidad(token, lote_id)  # 7a
    test_datos_invalidos_peso(token, lote_id)      # 7b
    test_lote_inexistente(token)                   # 8
    bm_id = test_crear_biometria(token, lote_id, fecha_siembra)  # 2
    if bm_id:
        test_get_by_id(token, bm_id)               # 3
        test_asociacion_lote(bm_id, lote_id)       # 6
        test_auditoria(bm_id)                      # 11
    test_listar(token)                             # 4
    test_listar_filtrado(token, lote_id)           # 5
    test_rol_sin_permiso(lote_id)                  # 10
    test_postgresql_integridad()                   # 12

    # Resumen
    print("\n" + "="*60)
    passed = sum(1 for _, _, ok, _ in results if ok)
    total = len(results)
    print(f"  Resultado: {passed}/{total} pruebas aprobadas")
    print("="*60)

    # Limpiar datos de prueba
    limpiar_datos_prueba()

    sys.exit(0 if passed == total else 1)
