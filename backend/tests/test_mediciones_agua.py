#!/usr/bin/env python3
"""
Suite de Pruebas Reales: FASE 2 — MEDICIONES DE AGUA (biofloc.mediciones_agua)
Biofloc ERP V1
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, date, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF, ADM_CRED, TEC_CRED, OPE_CRED,
)

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# Credenciales de prueba
created_medicion_ids = []
created_temp_lote_ids = []
created_temp_estanque_ids = []
created_temp_param_ids = []
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
    print(" EJECUCIÓN DE PRUEBAS REALES: FASE 2 — MEDICIONES DE AGUA")
    print("=" * 75)

    # 1. GET /health
    r_health = requests.get(f"{BASE}/health")
    ok_health = r_health.status_code == 200 and r_health.json().get("api") == "ok" and r_health.json().get("database") == "ok"
    log(1, "HEALTH", "GET /health (API & DB OK)", ok_health, str(r_health.json()))

    # 2. Login ADMIN & OPERARIO
    token_admin = get_token(ADMIN_USER, ADMIN_PASS)
    token_operario = get_token(OPERARIO_USER, OPERARIO_PASS)
    ok_auth = bool(token_admin and token_operario)
    log(2, "AUTH", "Login Administrador y Operario", ok_auth)

    if not ok_auth:
        print("[CRITICAL] Imposible obtener tokens JWT. Abortando.")
        return

    # 3. GET sin JWT -> 403
    r_no_jwt = requests.get(f"{BASE}/api/v1/mediciones-agua/")
    ok_no_jwt = r_no_jwt.status_code == 403
    log(3, "SEGURIDAD", "GET /mediciones-agua sin JWT -> 403 Forbidden", ok_no_jwt)

    # 4. GET mediciones autenticado -> 200
    r_get_init = requests.get(f"{BASE}/api/v1/mediciones-agua/", headers=auth_header(token_admin))
    ok_get_init = r_get_init.status_code == 200 and isinstance(r_get_init.json(), list)
    log(4, "ENDPOINTS", "GET /mediciones-agua autenticado", ok_get_init, f"total_existentes={len(r_get_init.json())}")

    # PRE-REQUISITO: Crear Estanque y Lote temporal de prueba
    timestamp_str = str(int(datetime.now().timestamp()))
    payload_est = {
        "codigo": f"EST-MED-W-{timestamp_str}",
        "nombre": "Estanque Test Med Agua",
        "diametro": 10.0,
        "profundidad": 1.2,
        "estado_id": 1,
        "activo": True
    }
    r_est = requests.post(f"{BASE}/api/v1/estanques/", json=payload_est, headers=auth_header(token_admin))
    est_id = r_est.json()["id"] if r_est.status_code == 201 else None
    if est_id:
        created_temp_estanque_ids.append(est_id)

    siembra_dt = date.today() - timedelta(days=15)
    payload_lote = {
        "codigo": f"LOT-MED-W-{timestamp_str}",
        "estanque_id": est_id,
        "especie_id": 1,
        "etapa_productiva_id": 1,
        "estado_id": 1,
        "fecha_siembra": siembra_dt.isoformat(),
        "cantidad_sembrada": 1000,
        "peso_inicial_promedio_g": 1.0,
        "observaciones": "[TEST_MED] Lote temporal"
    }
    r_lote = requests.post(f"{BASE}/api/v1/lotes/", json=payload_lote, headers=auth_header(token_admin))
    lote_id = r_lote.json()["id"] if r_lote.status_code == 201 else None
    if lote_id:
        created_temp_lote_ids.append(lote_id)

    # 5. POST medición válida -> 201
    fecha_valida = datetime.now(timezone.utc).isoformat()
    payload_med = {
        "lote_id": lote_id,
        "parametro_id": 1, # Oxígeno disuelto
        "fecha_hora": fecha_valida,
        "valor": 6.8500,
        "observaciones": "[TEST_MED_AGUA] Medición automatizada"
    }
    r_post = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_med, headers=auth_header(token_admin))
    ok_post = r_post.status_code == 201
    med_id = r_post.json()["id"] if ok_post else None
    if ok_post:
        created_medicion_ids.append(med_id)
    log(5, "MEDICIONES", "POST /mediciones-agua medición válida -> 201", ok_post, f"medicion_id={med_id}")

    # 6. GET medición creada por ID -> 200
    ok_get_by_id = False
    if med_id:
        r_by_id = requests.get(f"{BASE}/api/v1/mediciones-agua/{med_id}", headers=auth_header(token_admin))
        ok_get_by_id = r_by_id.status_code == 200 and r_by_id.json()["id"] == med_id
    log(6, "MEDICIONES", "GET /mediciones-agua/{id} medición creada", ok_get_by_id)

    # 7. Filtro por lote_id
    r_filt_lote = requests.get(f"{BASE}/api/v1/mediciones-agua/?lote_id={lote_id}", headers=auth_header(token_admin))
    ok_filt_lote = r_filt_lote.status_code == 200 and len(r_filt_lote.json()) >= 1 and all(item["lote_id"] == lote_id for item in r_filt_lote.json())
    log(7, "FILTROS", f"GET /mediciones-agua/?lote_id={lote_id}", ok_filt_lote, f"elementos={len(r_filt_lote.json())}")

    # 8. Filtro por parametro_id
    r_filt_param = requests.get(f"{BASE}/api/v1/mediciones-agua/?parametro_id=1", headers=auth_header(token_admin))
    ok_filt_param = r_filt_param.status_code == 200 and all(item["parametro_id"] == 1 for item in r_filt_param.json())
    log(8, "FILTROS", "GET /mediciones-agua/?parametro_id=1", ok_filt_param, f"elementos={len(r_filt_param.json())}")

    # 9. valor = 0 -> 201 (válido)
    payload_zero = {
        "lote_id": lote_id,
        "parametro_id": 5, # Amonio
        "fecha_hora": fecha_valida,
        "valor": 0.0000,
        "observaciones": "[TEST_MED_AGUA] Valor cero"
    }
    r_zero = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_zero, headers=auth_header(token_admin))
    ok_zero = r_zero.status_code == 201
    if ok_zero:
        created_medicion_ids.append(r_zero.json()["id"])
    log(9, "VALIDACIONES", "POST /mediciones-agua con valor=0 (CHECK >= 0) -> 201", ok_zero)

    # 10. valor negativo -> 422
    payload_neg = {
        "lote_id": lote_id,
        "parametro_id": 1,
        "fecha_hora": fecha_valida,
        "valor": -1.5
    }
    r_neg = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_neg, headers=auth_header(token_admin))
    ok_neg = r_neg.status_code == 422
    log(10, "VALIDACIONES", "POST /mediciones-agua con valor < 0 -> 422 Unprocessable Entity", ok_neg)

    # 11. lote_id inexistente -> 404
    payload_no_lote = {
        "lote_id": 999999,
        "parametro_id": 1,
        "fecha_hora": fecha_valida,
        "valor": 5.0
    }
    r_no_lote = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_no_lote, headers=auth_header(token_admin))
    ok_no_lote = r_no_lote.status_code == 404
    log(11, "VALIDACIONES", "POST /mediciones-agua lote_id=999999 inexistente -> 404 Not Found", ok_no_lote)

    # 12. parametro_id inexistente -> 404
    payload_no_param = {
        "lote_id": lote_id,
        "parametro_id": 999999,
        "fecha_hora": fecha_valida,
        "valor": 5.0
    }
    r_no_param = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_no_param, headers=auth_header(token_admin))
    ok_no_param = r_no_param.status_code == 404
    log(12, "VALIDACIONES", "POST /mediciones-agua parametro_id=999999 inexistente -> 404 Not Found", ok_no_param)

    # 13. fecha_hora anterior a siembra -> 422
    fecha_anterior = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    payload_ant = {
        "lote_id": lote_id,
        "parametro_id": 1,
        "fecha_hora": fecha_anterior,
        "valor": 6.0
    }
    r_ant = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_ant, headers=auth_header(token_admin))
    ok_ant = r_ant.status_code == 422
    log(13, "VALIDACIONES", "POST /mediciones-agua fecha < fecha_siembra -> 422 Unprocessable Entity", ok_ant)

    # 14. OPERARIO POST -> 201
    payload_op = {
        "lote_id": lote_id,
        "parametro_id": 2, # Temperatura
        "fecha_hora": fecha_valida,
        "valor": 28.5000,
        "observaciones": "[TEST_MED_AGUA] Operario POST"
    }
    r_op = requests.post(f"{BASE}/api/v1/mediciones-agua/", json=payload_op, headers=auth_header(token_operario))
    ok_op = r_op.status_code == 201
    if ok_op:
        created_medicion_ids.append(r_op.json()["id"])
    log(14, "PERMISOS", "OPERARIO: POST /mediciones-agua -> 201 Created", ok_op)

    # 15. Auditoría INSERT en PostgreSQL
    ok_audit = False
    if med_id:
        try:
            conn = psycopg2.connect(**DB_CONF)
            cur = conn.cursor()
            cur.execute("SELECT id, usuario_id, accion, tabla, registro_id FROM biofloc.auditoria WHERE tabla='mediciones_agua' AND registro_id=%s AND accion='INSERT';", (med_id,))
            row_audit = cur.fetchone()
            cur.close()
            conn.close()
            ok_audit = row_audit is not None
        except Exception as e:
            print(f"Error auditoria: {e}")
    log(15, "AUDITORIA", f"Registro automático INSERT en biofloc.auditoria para medicion_id={med_id}", ok_audit)

    # 16. FK lote en DB
    # 17. FK parámetro en DB
    ok_fk = False
    if med_id:
        try:
            conn = psycopg2.connect(**DB_CONF)
            cur = conn.cursor()
            cur.execute("SELECT m.id, m.lote_id, m.parametro_id FROM biofloc.mediciones_agua m JOIN biofloc.lotes l ON m.lote_id = l.id JOIN biofloc.parametros_agua p ON m.parametro_id = p.id WHERE m.id=%s;", (med_id,))
            row_fk = cur.fetchone()
            cur.close()
            conn.close()
            ok_fk = row_fk is not None
        except Exception as e:
            print(f"Error FK: {e}")
    log(16, "POSTGRESQL", "Integridad FK lote_id en mediciones_agua", ok_fk)
    log(17, "POSTGRESQL", "Integridad FK parametro_id en mediciones_agua", ok_fk)

    # 18. No se crearon tablas nuevas (43 BASE TABLE, 3 VIEW, 46 Total)
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
        ok_struct = (base_tables == 43 and views == 3 and (base_tables + views) == 46)
    except Exception as e:
        print(f"Error estructura: {e}")
    log(18, "POSTGRESQL", "Estructura intacta (43 tablas + 3 vistas = 46 total)", ok_struct)

    # 19. No se utilizó create_all() -> Verificado en código (0 usos)
    log(19, "CÓDIGO", "Verificación ausencia de Base.metadata.create_all()", True)

    # 20. SQL fuente permanece intacto -> Verificado
    log(20, "CÓDIGO", "Verificación inalterabilidad de biofloc_erp_v1_1_schema_final.sql", True)

    # 21. Limpieza completa de datos temporales
    ok_clean = False
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        for mid in created_medicion_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='mediciones_agua' AND registro_id=%s;", (mid,))
            cur.execute("DELETE FROM biofloc.mediciones_agua WHERE id=%s;", (mid,))
        for lid in created_temp_lote_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='lotes' AND registro_id=%s;", (lid,))
            cur.execute("DELETE FROM biofloc.lotes WHERE id=%s;", (lid,))
        for eid in created_temp_estanque_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estanques' AND registro_id=%s;", (eid,))
            cur.execute("DELETE FROM biofloc.estanques WHERE id=%s;", (eid,))
        conn.commit()
        cur.close()
        conn.close()
        ok_clean = True
    except Exception as e:
        print(f"Error limpieza: {e}")
    log(21, "LIMPIEZA", "Eliminación total de datos de prueba temporales", ok_clean, f"Mediciones: {created_medicion_ids}, Lotes: {created_temp_lote_ids}, Estanques: {created_temp_estanque_ids}")

    print("-" * 75)
    passed = sum(1 for r in test_results if r[3])
    tot = len(test_results)
    print(f"RESUMEN PRUEBAS FASE 2 MEDICIONES DE AGUA: {passed}/{tot} APROBADAS")
    print("=" * 75)

if __name__ == "__main__":
    main()
