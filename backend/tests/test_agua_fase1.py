#!/usr/bin/env python3
"""
Suite de Pruebas Reales: FASE 1 — Agua (parametros_agua, referencias_agua)
Biofloc ERP V1
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# Credenciales existentes
ADMIN_USER = "admin@biofloc.com"
ADMIN_PASS = "AdminBiofloc2026!"
OPERARIO_USER = "operario_test@biofloc.com"
OPERARIO_PASS = "Operario1234!"

DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")

created_param_ids = []
created_ref_ids = []
test_results = []

def log(num, category, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    num_str = f"{num:02d}"
    msg = f"  {icon} [{num_str}] [{category}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    test_results.append((num, category, name, ok, detail))

def get_token(correo, password):
    try:
        r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": correo, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
    except Exception as e:
        print(f"Error login: {e}")
    return None

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def main():
    print("=" * 75)
    print(" EJECUCIÓN DE PRUEBAS REALES: FASE 1 — AGUA (PARAMETROS & REFERENCIAS)")
    print("=" * 75)

    # 1. Imports y Salud
    r = requests.get(f"{BASE}/health")
    ok_health = r.status_code == 200 and r.json().get("api") == "ok" and r.json().get("database") == "ok"
    log(1, "HEALTH", "FastAPI + DB Conexión GET /health", ok_health, str(r.json()))

    # 2. Login Admin
    token_admin = get_token(ADMIN_USER, ADMIN_PASS)
    token_operario = get_token(OPERARIO_USER, OPERARIO_PASS)
    ok_auth = bool(token_admin and token_operario)
    log(2, "AUTH", "Login Administrador y Operario", ok_auth)

    if not ok_auth:
        print("[CRITICAL] Imposible obtener tokens JWT. Abortando.")
        return

    # 3. GET sin JWT -> 403 Forbidden
    r_param_no_jwt = requests.get(f"{BASE}/api/v1/parametros-agua/")
    r_ref_no_jwt = requests.get(f"{BASE}/api/v1/referencias-agua/")
    ok_no_jwt = (r_param_no_jwt.status_code == 403 and r_ref_no_jwt.status_code == 403)
    log(3, "SEGURIDAD", "GET sin JWT -> 403 Forbidden", ok_no_jwt)

    # 4. GET Autenticado
    r_param_get = requests.get(f"{BASE}/api/v1/parametros-agua/", headers=auth_header(token_admin))
    r_ref_get = requests.get(f"{BASE}/api/v1/referencias-agua/", headers=auth_header(token_admin))
    ok_get = (r_param_get.status_code == 200 and r_ref_get.status_code == 200)
    log(4, "ENDPOINTS", "GET /parametros-agua y GET /referencias-agua autenticado", ok_get, f"Parametros: {len(r_param_get.json())}, Referencias: {len(r_ref_get.json())}")

    # 5. POST ParametroAgua Válido
    param_name = f"Parametro Test {int(datetime.now().timestamp())}"
    payload_param = {
        "nombre": param_name,
        "unidad": "mg/L",
        "descripcion": "Parámetro de prueba automatizada",
        "activo": True
    }
    r_param_post = requests.post(f"{BASE}/api/v1/parametros-agua/", json=payload_param, headers=auth_header(token_admin))
    ok_param_post = r_param_post.status_code == 201
    param_id = r_param_post.json()["id"] if ok_param_post else None
    if ok_param_post:
        created_param_ids.append(param_id)
    log(5, "PARAMETROS", "POST /parametros-agua válido", ok_param_post, f"param_id={param_id}")

    # 6. PUT ParametroAgua Válido
    ok_param_put = False
    if param_id:
        payload_param_put = {"descripcion": "Descripción actualizada de prueba"}
        r_param_put = requests.put(f"{BASE}/api/v1/parametros-agua/{param_id}", json=payload_param_put, headers=auth_header(token_admin))
        ok_param_put = r_param_put.status_code == 200 and r_param_put.json()["descripcion"] == "Descripción actualizada de prueba"
    log(6, "PARAMETROS", "PUT /parametros-agua/{id} válido", ok_param_put)

    # 7. POST ReferenciaAgua Válida
    payload_ref = {
        "especie_id": 1,
        "etapa_productiva_id": 1,
        "parametro_id": param_id if param_id else 1,
        "valor_minimo": 5.5000,
        "valor_maximo": 9.0000,
        "observaciones": "Referencia de prueba automatizada",
        "activo": True
    }
    r_ref_post = requests.post(f"{BASE}/api/v1/referencias-agua/", json=payload_ref, headers=auth_header(token_admin))
    ok_ref_post = r_ref_post.status_code == 201
    ref_id = r_ref_post.json()["id"] if ok_ref_post else None
    if ok_ref_post:
        created_ref_ids.append(ref_id)
    log(7, "REFERENCIAS", "POST /referencias-agua válida", ok_ref_post, f"referencia_id={ref_id}")

    # 8. PUT ReferenciaAgua Válida
    ok_ref_put = False
    if ref_id:
        payload_ref_put = {"valor_maximo": 9.5000, "observaciones": "Actualizado en test"}
        r_ref_put = requests.put(f"{BASE}/api/v1/referencias-agua/{ref_id}", json=payload_ref_put, headers=auth_header(token_admin))
        ok_ref_put = r_ref_put.status_code == 200 and float(r_ref_put.json()["valor_maximo"]) == 9.5
    log(8, "REFERENCIAS", "PUT /referencias-agua/{id} válida", ok_ref_put)

    # 9. Pruebas Rol OPERARIO (GET 200, POST 403, PUT 403)
    r_op_get = requests.get(f"{BASE}/api/v1/parametros-agua/", headers=auth_header(token_operario))
    r_op_post = requests.post(f"{BASE}/api/v1/parametros-agua/", json=payload_param, headers=auth_header(token_operario))
    r_op_put = requests.put(f"{BASE}/api/v1/parametros-agua/{param_id}", json=payload_param_put, headers=auth_header(token_operario))
    ok_operario = (r_op_get.status_code == 200 and r_op_post.status_code == 403 and r_op_put.status_code == 403)
    log(9, "PERMISOS", "OPERARIO: GET (200), POST (403), PUT (403)", ok_operario)

    # 10. Validación valor_minimo > valor_maximo -> 422
    payload_inv_rango = {
        "especie_id": 1,
        "etapa_productiva_id": 2,
        "parametro_id": param_id if param_id else 1,
        "valor_minimo": 10.0,
        "valor_maximo": 2.0
    }
    r_inv_rango = requests.post(f"{BASE}/api/v1/referencias-agua/", json=payload_inv_rango, headers=auth_header(token_admin))
    ok_inv_rango = r_inv_rango.status_code == 422
    log(10, "VALIDACIONES", "valor_minimo > valor_maximo -> 422 Unprocessable Entity", ok_inv_rango, f"status={r_inv_rango.status_code}")

    # 11. Validación FK inexistente -> 404
    payload_inv_fk = {
        "especie_id": 999999,
        "etapa_productiva_id": 1,
        "parametro_id": 1,
        "valor_minimo": 1.0,
        "valor_maximo": 5.0
    }
    r_inv_fk = requests.post(f"{BASE}/api/v1/referencias-agua/", json=payload_inv_fk, headers=auth_header(token_admin))
    ok_inv_fk = r_inv_fk.status_code == 404
    log(11, "VALIDACIONES", "FK especie_id=999999 inexistente -> 404 Not Found", ok_inv_fk, f"status={r_inv_fk.status_code}")

    # 12. Duplicación de especie + etapa + parametro -> 400
    r_dup = requests.post(f"{BASE}/api/v1/referencias-agua/", json=payload_ref, headers=auth_header(token_admin))
    ok_dup = r_dup.status_code == 400
    log(12, "VALIDACIONES", "Duplicidad (especie, etapa, parametro) -> 400 Bad Request", ok_dup, f"status={r_dup.status_code}")

    # 13 y 14. Verificar Auditoría en PostgreSQL (INSERT & UPDATE)
    ok_audit_ins = False
    ok_audit_upd = False
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        
        # Check INSERT
        cur.execute("SELECT id FROM biofloc.auditoria WHERE tabla='parametros_agua' AND registro_id=%s AND accion='INSERT';", (param_id,))
        row_ins = cur.fetchone()
        ok_audit_ins = row_ins is not None
        
        # Check UPDATE
        cur.execute("SELECT id FROM biofloc.auditoria WHERE tabla='parametros_agua' AND registro_id=%s AND accion='UPDATE';", (param_id,))
        row_upd = cur.fetchone()
        ok_audit_upd = row_upd is not None

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error consultando auditoria DB: {e}")

    log(13, "AUDITORIA", "Registro de auditoría INSERT en biofloc.auditoria", ok_audit_ins)
    log(14, "AUDITORIA", "Registro de auditoría UPDATE en biofloc.auditoria", ok_audit_upd)

    # 15. Estructura de PostgreSQL sin alteración (42 BASE TABLE, 4 VIEW, 46 Total)
    ok_struct = False
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("SELECT table_type, count(*) FROM information_schema.tables WHERE table_schema='biofloc' GROUP BY table_type;")
        rows = dict(cur.fetchall())
        cur.close()
        conn.close()
        base_tables = rows.get("BASE TABLE", 0)
        views = rows.get("VIEW", 0)
        ok_struct = (base_tables == 42 and views == 4 and (base_tables + views) == 46)
    except Exception as e:
        print(f"Error consultando estructura DB: {e}")
    log(15, "POSTGRESQL", "Estructura intacta (42 tablas + 4 vistas = 46 total)", ok_struct)

    # 16. Limpieza de datos temporales
    ok_clean = False
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        for rid in created_ref_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='referencias_agua' AND registro_id=%s;", (rid,))
            cur.execute("DELETE FROM biofloc.referencias_agua WHERE id=%s;", (rid,))
        for pid in created_param_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='parametros_agua' AND registro_id=%s;", (pid,))
            cur.execute("DELETE FROM biofloc.parametros_agua WHERE id=%s;", (pid,))
        conn.commit()
        cur.close()
        conn.close()
        ok_clean = True
    except Exception as e:
        print(f"Error limpiando datos: {e}")
    log(16, "LIMPIEZA", "Eliminación total de datos de prueba temporales", ok_clean, f"Parametros: {created_param_ids}, Referencias: {created_ref_ids}")

    print("-" * 75)
    passed = sum(1 for r in test_results if r[3])
    tot = len(test_results)
    print(f"RESUMEN PRUEBAS FASE 1 AGUA: {passed}/{tot} APROBADAS")
    print("=" * 75)

if __name__ == "__main__":
    main()
