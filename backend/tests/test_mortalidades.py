#!/usr/bin/env python3
"""
Script de pruebas reales para el bloque Mortalidades — Biofloc ERP V1
Ejecutar: python test_mortalidades.py

Pruebas:
 1. Login real + JWT
 2. POST mortalidad válida
 3. GET mortalidad por ID
 4. GET listado
 5. GET listado filtrado por lote_id
 6. Asociación correcta con lote
 7. Datos inválidos (cantidad=0)
 8. Lote inexistente
 9. Acceso sin JWT
10. Rol con permiso (OPERARIO)
11. Auditoría en PostgreSQL
12. Validación de PostgreSQL (no se crearon tablas extra)
13. GET /health
14. Validación regla de negocio (Mortalidad > Población)
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, timezone

# Forzar utf-8 stdout para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Credenciales de prueba
# ---------------------------------------------------------------------------
# DB directa para validaciones
DB_SCHEMA = "biofloc"

TEST_MORTALIDAD_IDS = []

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
# PRE-REQUISITO: obtener un lote_id válido de la BD
# ---------------------------------------------------------------------------
def obtener_lote_valido():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        # Obtener el lote con ID 7 que usamos antes
        cur.execute("SELECT id, fecha_siembra, cantidad_sembrada FROM biofloc.lotes WHERE id = 7;")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        print(f"  [WARN] No se pudo conectar a PostgreSQL: {e}")
        return None

def test_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == "ok"
    log(13, "GET /health", ok, str(r.json()))

def test_login():
    token = get_token(ADMIN_USER, ADMIN_PASS)
    ok = token is not None
    log(1, f"Login ADMINISTRADOR ({ADMIN_USER})", ok, f"token={'...'+token[-12:] if token else 'NONE'}")
    return token

def test_sin_jwt():
    r = requests.get(f"{BASE}/api/v1/mortalidades/")
    ok = r.status_code == 403
    log(9, "GET /mortalidades sin JWT -> 403", ok, f"status={r.status_code}")

def test_datos_invalidos_cantidad(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad": 0,
        "causa": "Prueba"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(7, "POST mortalidad con cantidad=0 -> 422", ok, f"status={r.status_code}")

def test_lote_inexistente(token):
    payload = {
        "lote_id": 999999,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad": 10,
        "causa": "Prueba"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload, headers=auth_header(token))
    ok = r.status_code == 404
    log(8, "POST mortalidad con lote_id=999999 -> 404", ok, f"status={r.status_code} | {r.text[:80]}")

def test_crear_mortalidad(token, lote_id):
    fecha_hora = datetime.now(timezone.utc).isoformat()
    payload = {
        "lote_id": lote_id,
        "fecha_hora": fecha_hora,
        "cantidad": 50,
        "causa": "Prueba de enfermedad",
        "observaciones": "[TEST_MORTALIDAD] Muestreo automatizado"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload, headers=auth_header(token))
    ok = r.status_code == 201
    m_id = None
    if ok:
        data = r.json()
        m_id = data["id"]
        TEST_MORTALIDAD_IDS.append(m_id)
        detail = f"id={m_id} lote_id={data['lote_id']} cantidad={data['cantidad']}"
    else:
        detail = f"status={r.status_code} | {r.text[:120]}"
    log(2, "POST mortalidad valida -> 201", ok, detail)
    return m_id

def test_get_by_id(token, m_id):
    r = requests.get(f"{BASE}/api/v1/mortalidades/{m_id}", headers=auth_header(token))
    ok = r.status_code == 200
    if ok:
        data = r.json()
        detail = f"id={data['id']} lote_id={data['lote_id']} created_at={data['created_at']}"
    else:
        detail = f"status={r.status_code} | {r.text[:80]}"
    log(3, f"GET /mortalidades/{m_id}", ok, detail)

def test_listar(token):
    r = requests.get(f"{BASE}/api/v1/mortalidades/", headers=auth_header(token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    log(4, "GET /mortalidades/ (listado completo)", ok, f"registros={len(r.json()) if ok else 'ERROR'}")

def test_listar_filtrado(token, lote_id):
    r = requests.get(f"{BASE}/api/v1/mortalidades/?lote_id={lote_id}", headers=auth_header(token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    if ok:
        todos_del_lote = all(m["lote_id"] == lote_id for m in r.json())
        ok = ok and todos_del_lote
        detail = f"registros={len(r.json())} todos_lote_id_correcto={todos_del_lote}"
    else:
        detail = f"status={r.status_code}"
    log(5, f"GET /mortalidades/?lote_id={lote_id} (filtrado)", ok, detail)

def test_asociacion_lote(m_id, lote_id):
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            "SELECT lote_id FROM biofloc.mortalidades WHERE id = %s;", (m_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None and row[0] == lote_id
        detail = f"BD: mortalidades.lote_id={row[0] if row else 'NULL'} esperado={lote_id}"
    except Exception as e:
        ok = False
        detail = str(e)
    log(6, "Asociacion mortalidad↔lote en PostgreSQL", ok, detail)

def test_rol_operario(lote_id):
    token = get_token(OPERARIO_USER, OPERARIO_PASS)
    if not token:
        log(10, "Rol OPERARIO POST -> 201", False, "No se pudo obtener token OPERARIO")
        return
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad": 10,
        "causa": "Prueba de operario"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload, headers=auth_header(token))
    ok = r.status_code == 201
    if ok:
        m_id = r.json()["id"]
        TEST_MORTALIDAD_IDS.append(m_id)
        detail = f"status=201 id={m_id} (OPERARIO si tiene permiso)"
    else:
        detail = f"status={r.status_code} | {r.text[:80]}"
    log(10, "Rol OPERARIO POST /mortalidades -> 201", ok, detail)

def test_auditoria(m_id):
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, accion, tabla, registro_id FROM biofloc.auditoria "
            "WHERE tabla = 'mortalidades' AND registro_id = %s ORDER BY id DESC LIMIT 1;",
            (m_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None and row[1] == "INSERT" and row[2] == "mortalidades"
        detail = f"auditoria.id={row[0]} accion={row[1]} tabla={row[2]} registro_id={row[3]}" if row else "SIN REGISTRO"
    except Exception as e:
        ok = False
        detail = str(e)
    log(11, "Auditoria INSERT en biofloc.auditoria", ok, detail)

def test_regla_poblacion(token, lote_id, cantidad_sembrada):
    # Intentar registrar una mortalidad mayor a la cantidad sembrada
    fecha_hora = datetime.now(timezone.utc).isoformat()
    payload = {
        "lote_id": lote_id,
        "fecha_hora": fecha_hora,
        "cantidad": cantidad_sembrada + 100,
        "causa": "Prueba de poblacion"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(14, "POST mortalidad acumulada > sembrada -> 422", ok, f"status={r.status_code} | {r.text[:80]}")

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

def limpiar_datos_prueba():
    if not TEST_MORTALIDAD_IDS:
        print("\n  [INFO] No hay registros de prueba para eliminar.")
        return
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM biofloc.auditoria WHERE tabla = 'mortalidades' AND registro_id = ANY(%s);",
            (TEST_MORTALIDAD_IDS,)
        )
        cur.execute(
            "DELETE FROM biofloc.mortalidades WHERE id = ANY(%s);",
            (TEST_MORTALIDAD_IDS,)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"\n  [CLEAN] Limpieza: eliminadas {len(TEST_MORTALIDAD_IDS)} mortalidad(es) de prueba: {TEST_MORTALIDAD_IDS}")
    except Exception as e:
        print(f"  [WARN] Error durante limpieza: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  BIOFLOC ERP V1 - Pruebas Mortalidades")
    print("="*60)

    try:
        requests.get(f"{BASE}/health", timeout=3)
    except Exception:
        print(f"\n  [ERROR] El servidor no esta corriendo en {BASE}")
        print("     Iniciar con: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)

    lote_row = obtener_lote_valido()
    if not lote_row:
        print("\n  [ERROR] No se pudo obtener un lote valido de la BD. Verificar conexion.")
        sys.exit(1)
    lote_id, fecha_siembra, cantidad_sembrada = lote_row
    print(f"\n  [INFO] Usando lote_id={lote_id} (fecha_siembra={fecha_siembra}, cantidad_sembrada={cantidad_sembrada})\n")

    test_health()                                  # 13
    token = test_login()                           # 1
    if not token:
        print("\n  [ERROR] Login fallo. Verificar credenciales en el script.")
        sys.exit(1)

    test_sin_jwt()                                 # 9
    test_datos_invalidos_cantidad(token, lote_id)  # 7
    test_lote_inexistente(token)                   # 8
    m_id = test_crear_mortalidad(token, lote_id)   # 2
    if m_id:
        test_get_by_id(token, m_id)                # 3
        test_asociacion_lote(m_id, lote_id)        # 6
        test_auditoria(m_id)                       # 11
    test_listar(token)                             # 4
    test_listar_filtrado(token, lote_id)           # 5
    test_rol_operario(lote_id)                     # 10
    test_regla_poblacion(token, lote_id, cantidad_sembrada) # 14
    test_postgresql_integridad()                   # 12

    print("\n" + "="*60)
    passed = sum(1 for _, _, ok, _ in results if ok)
    total = len(results)
    print(f"  Resultado: {passed}/{total} pruebas aprobadas")
    print("="*60)

    limpiar_datos_prueba()

    sys.exit(0 if passed == total else 1)
