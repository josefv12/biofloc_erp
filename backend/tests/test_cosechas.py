#!/usr/bin/env python3
"""
Script de pruebas reales para el bloque Cosechas — Biofloc ERP V1
Ejecutar: python test_cosechas.py

Pruebas:
 1. Login real + JWT
 2. POST cosecha válida
 3. GET cosecha por ID
 4. GET listado
 5. GET listado filtrado por lote_id
 6. Lote inexistente
 7. Datos inválidos (tipos incorrectos)
 8. Cantidad inválida (CHECK cantidad_peces > 0)
 9. Peso inválido (CHECK peso_total_kg > 0)
10. Acceso sin JWT (403)
11. Permisos por rol (OPERARIO)
12. Auditoría en PostgreSQL (INSERT en biofloc.auditoria)
13. Integridad de FK (registrado_por, lote_id)
14. GET /health
15. Conteo y validación de estructura (42 tablas, 4 vistas, 46 total)
16. Limpieza total de datos de prueba
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# Credenciales de prueba
DB_SCHEMA = "biofloc"

TEST_COSECHA_IDS = []
results = []

PASS_ICON = "[OK]"
FAIL_ICON = "[FAIL]"

def log(num, name, ok, detail=""):
    icon = PASS_ICON if ok else FAIL_ICON
    num_str = str(num) if not isinstance(num, int) else f"{num:02d}"
    msg = f"  {icon} [{num_str}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    results.append((num, name, ok, detail))

def get_token(correo, password):
    try:
        r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": correo, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
    except Exception as e:
        print(f"Error al conectar con endpoint de login: {e}")
    return None

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def obtener_lote_valido():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT id FROM biofloc.lotes ORDER BY id LIMIT 1;")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"  [WARN] No se pudo conectar a PostgreSQL: {e}")
        return None

def test_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == "ok" and r.json().get("database") == "ok"
    log(14, "GET /health (API & DB OK)", ok, str(r.json()))

def test_login():
    token = get_token(ADMIN_USER, ADMIN_PASS)
    ok = token is not None
    log(1, f"Login ADMINISTRADOR ({ADMIN_USER})", ok, f"token={'...'+token[-12:] if token else 'NONE'}")
    return token

def test_jwt(token):
    r = requests.get(f"{BASE}/api/v1/cosechas/", headers=auth_header(token))
    ok = r.status_code == 200
    log(2, "Verificación Token JWT válido", ok, f"status={r.status_code}")

def test_sin_jwt():
    r = requests.get(f"{BASE}/api/v1/cosechas/")
    ok = r.status_code == 403
    log(10, "GET /cosechas sin JWT -> 403 Forbidden", ok, f"status={r.status_code}")

def test_crear_cosecha_valida(token, lote_id):
    fecha_hora = datetime.now(timezone.utc).isoformat()
    payload = {
        "lote_id": lote_id,
        "fecha_hora": fecha_hora,
        "cantidad_peces": 120,
        "peso_total_kg": 60.500,
        "peso_promedio_g": 504.000,
        "observaciones": "[TEST_COSECHA] Cosecha de prueba automatizada"
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token))
    ok = r.status_code == 201
    cid = None
    if ok:
        data = r.json()
        cid = data["id"]
        TEST_COSECHA_IDS.append(cid)
    log(3, "POST /cosechas cosecha válida", ok, f"status={r.status_code} | id={cid}")
    return cid

def test_obtener_cosecha_por_id(token, cosecha_id):
    r = requests.get(f"{BASE}/api/v1/cosechas/{cosecha_id}", headers=auth_header(token))
    ok = r.status_code == 200 and r.json().get("id") == cosecha_id
    log(4, f"GET /cosechas/{cosecha_id} por ID", ok, f"status={r.status_code}")

def test_obtener_listado(token):
    r = requests.get(f"{BASE}/api/v1/cosechas/", headers=auth_header(token))
    ok = r.status_code == 200 and isinstance(r.json(), list)
    log(5, "GET /cosechas listado general", ok, f"status={r.status_code} | total_items={len(r.json()) if ok else 0}")

def test_filtro_por_lote(token, lote_id):
    r = requests.get(f"{BASE}/api/v1/cosechas/?lote_id={lote_id}", headers=auth_header(token))
    ok = r.status_code == 200 and all(item["lote_id"] == lote_id for item in r.json())
    log(6, f"GET /cosechas/?lote_id={lote_id} (Filtro)", ok, f"status={r.status_code} | items_filtrados={len(r.json()) if ok else 0}")

def test_lote_inexistente(token):
    payload = {
        "lote_id": 999999,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_peces": 100,
        "peso_total_kg": 50.0
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token))
    ok = r.status_code == 404
    log(7, "POST /cosechas con lote_id inexistente -> 404", ok, f"status={r.status_code} | {r.text[:80]}")

def test_datos_invalidos(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": "fecha-invalida",
        "cantidad_peces": "cien",
        "peso_total_kg": 50.0
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(8, "POST /cosechas con datos con formato inválido -> 422", ok, f"status={r.status_code}")

def test_cantidad_invalida_check(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_peces": 0,
        "peso_total_kg": 50.0
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(9, "POST /cosechas con cantidad_peces=0 (CHECK > 0) -> 422", ok, f"status={r.status_code}")

def test_peso_invalido_check(token, lote_id):
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_peces": 10,
        "peso_total_kg": -5.0
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token))
    ok = r.status_code == 422
    log(10, "POST /cosechas con peso_total_kg <= 0 (CHECK > 0) -> 422", ok, f"status={r.status_code}")

def test_permisos_operario(lote_id):
    token_op = get_token(OPERARIO_USER, OPERARIO_PASS)
    if not token_op:
        log(11, f"Rol OPERARIO ({OPERARIO_USER})", False, "No se pudo obtener token de operario")
        return
    payload = {
        "lote_id": lote_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "cantidad_peces": 50,
        "peso_total_kg": 25.0,
        "observaciones": "[TEST_COSECHA] Operario test"
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload, headers=auth_header(token_op))
    ok = r.status_code == 201
    if ok:
        TEST_COSECHA_IDS.append(r.json()["id"])
    log(11, f"POST /cosechas como OPERARIO -> 201", ok, f"status={r.status_code}")

def test_auditoria_postgresql(cosecha_id):
    if not cosecha_id:
        log(12, "Auditoría en PostgreSQL (biofloc.auditoria)", False, "Sin ID de cosecha")
        return
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT id, usuario_id, accion, tabla, registro_id FROM biofloc.auditoria WHERE tabla='cosechas' AND registro_id=%s AND accion='INSERT';", (cosecha_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None
        log(12, f"Auditoría en PostgreSQL registro_id={cosecha_id}", ok, f"auditoria_id={row[0] if row else 'NONE'}")
    except Exception as e:
        log(12, "Auditoría en PostgreSQL", False, str(e))

def test_integridad_fk(cosecha_id):
    if not cosecha_id:
        log(13, "Integridad de FK en PostgreSQL", False, "Sin ID de cosecha")
        return
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT c.id, c.lote_id, c.registrado_por FROM biofloc.cosechas c JOIN biofloc.lotes l ON c.lote_id = l.id JOIN biofloc.usuarios u ON c.registrado_por = u.id WHERE c.id=%s;", (cosecha_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        ok = row is not None
        log(13, f"Integridad FK (lote & usuario) en cosecha id={cosecha_id}", ok, f"FKs intactas: {row}")
    except Exception as e:
        log(13, "Integridad FK", False, str(e))

def test_estructura_postgresql():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT table_type, count(*) FROM information_schema.tables WHERE table_schema='biofloc' GROUP BY table_type;")
        rows = dict(cur.fetchall())
        cur.close()
        conn.close()
        base_tables = rows.get("BASE TABLE", 0)
        views = rows.get("VIEW", 0)
        total = base_tables + views
        ok = (base_tables == 42 and views == 4 and total == 46)
        log(15, f"Estructura PostgreSQL ({base_tables} tablas + {views} vistas = {total} total)", ok, f"BASE TABLE: {base_tables}, VIEW: {views}, TOTAL: {total}")
    except Exception as e:
        log(15, "Estructura PostgreSQL", False, str(e))

def limpiar_datos_prueba():
    if not TEST_COSECHA_IDS:
        log(16, "Limpieza de datos de prueba", True, "No se registraron IDs para borrar")
        return
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        for cid in TEST_COSECHA_IDS:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='cosechas' AND registro_id=%s;", (cid,))
            cur.execute("DELETE FROM biofloc.cosechas WHERE id=%s;", (cid,))
        conn.commit()
        cur.close()
        conn.close()
        log(16, f"Limpieza de datos de prueba ({len(TEST_COSECHA_IDS)} cosechas + auditoría borradas)", True, f"IDs limpiados: {TEST_COSECHA_IDS}")
    except Exception as e:
        log(16, "Limpieza de datos de prueba", False, str(e))

def main():
    print("=" * 70)
    print(" EJECUCIÓN DE PRUEBAS REALES: COSECHAS — BIOFLOC ERP V1")
    print("=" * 70)
    
    test_health()
    token = test_login()
    if not token:
        print("[CRITICAL] Imposible obtener token JWT. Abortando pruebas.")
        return

    test_jwt(token)
    test_sin_jwt()
    
    lote_id = obtener_lote_valido()
    if not lote_id:
        print("[CRITICAL] No hay lotes registrados en la BD para probar. Abortando.")
        return
        
    cid = test_crear_cosecha_valida(token, lote_id)
    test_obtener_cosecha_por_id(token, cid)
    test_obtener_listado(token)
    test_filtro_por_lote(token, lote_id)
    test_lote_inexistente(token)
    test_datos_invalidos(token, lote_id)
    test_cantidad_invalida_check(token, lote_id)
    test_peso_invalido_check(token, lote_id)
    test_permisos_operario(lote_id)
    
    test_auditoria_postgresql(cid)
    test_integridad_fk(cid)
    test_estructura_postgresql()
    limpiar_datos_prueba()
    
    print("-" * 70)
    tot = len(results)
    passed = sum(1 for r in results if r[2])
    failed = tot - passed
    print(f"RESUMEN FINAL: {passed}/{tot} PRUEBAS APROBADAS ({failed} FALLIDAS)")
    print("=" * 70)

if __name__ == "__main__":
    main()
