#!/usr/bin/env python3
"""
Audit Test Suite: Eje Producción Completo — Biofloc ERP V1
Auditoría técnica integral de los 6 módulos:
  1. Estanques
  2. Lotes
  3. Biometrías
  4. Mortalidades
  5. Alimentaciones
  6. Cosechas
"""
import sys
import io
import requests
import psycopg2
from datetime import datetime, date, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
HEADERS_JSON = {"Content-Type": "application/json"}

# Credenciales de prueba existentes
ADMIN_USER = "admin@biofloc.com"
ADMIN_PASS = "AdminBiofloc2026!"
OPERARIO_USER = "operario_test@biofloc.com"
OPERARIO_PASS = "Operario1234!"
TECNICO_USER = "tecnico_test@biofloc.com"
TECNICO_PASS = "Tecnico1234!"

DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")

audit_results = []
created_resources = {
    "cosechas": [],
    "alimentaciones": [],
    "mortalidades": [],
    "biometrias": [],
    "lotes": [],
    "estanques": []
}


def log_test(num, category, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    num_str = f"{num:02d}"
    msg = f"  {icon} [{num_str}] [{category}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    audit_results.append((num, category, name, ok, detail))


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


# ---------------------------------------------------------------------------
# 1. SALUD DE API Y BASE DE DATOS
# ---------------------------------------------------------------------------
def audit_health():
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("api") == "ok" and r.json().get("database") == "ok"
    log_test(1, "HEALTH", "GET /health", ok, str(r.json()))


# ---------------------------------------------------------------------------
# 2. AUTENTICACIÓN Y SEGURIDAD (JWT Y ROLES)
# ---------------------------------------------------------------------------
def audit_security():
    token_admin = get_token(ADMIN_USER, ADMIN_PASS)
    token_operario = get_token(OPERARIO_USER, OPERARIO_PASS)
    token_tecnico = get_token(TECNICO_USER, TECNICO_PASS)

    ok_tokens = bool(token_admin and token_operario and token_tecnico)
    log_test(2, "SEGURIDAD", "Login tokens para ADMIN, TECNICO, OPERARIO", ok_tokens)

    # Probar endpoint sin JWT
    endpoints = ["estanques", "lotes", "biometrias", "mortalidades", "alimentaciones", "cosechas"]
    all_403 = True
    for ep in endpoints:
        r = requests.get(f"{BASE}/api/v1/{ep}/")
        if r.status_code != 403:
            all_403 = False
            break
    log_test(3, "SEGURIDAD", "Acceso sin JWT denegado (403) en los 6 módulos", all_403)

    return token_admin, token_operario, token_tecnico


# ---------------------------------------------------------------------------
# 3. FLUJO PRODUCTIVO INTEGRAL Y AUDITORÍA
# ---------------------------------------------------------------------------
def audit_flujo_productivo(token_admin):
    # A. Estanque
    estanque_code = f"EST-AUDIT-{int(datetime.now().timestamp())}"
    payload_est = {
        "codigo": estanque_code,
        "nombre": "Estanque Audit Integral",
        "diametro": 12.0,
        "profundidad": 1.4,
        "estado_id": 1,
        "activo": True
    }
    r = requests.post(f"{BASE}/api/v1/estanques/", json=payload_est, headers=auth_header(token_admin))
    ok_est = r.status_code == 201
    estanque_id = r.json()["id"] if ok_est else None
    if ok_est:
        created_resources["estanques"].append(estanque_id)
    log_test(4, "FLUJO", "1/6 Creación de Estanque", ok_est, f"estanque_id={estanque_id}")

    if not estanque_id:
        return

    # B. Lote
    lote_code = f"LOT-AUDIT-{int(datetime.now().timestamp())}"
    siembra_dt = date.today() - timedelta(days=10)
    payload_lote = {
        "codigo": lote_code,
        "estanque_id": estanque_id,
        "especie_id": 1,
        "etapa_productiva_id": 1,
        "estado_id": 1,
        "fecha_siembra": siembra_dt.isoformat(),
        "cantidad_sembrada": 2000,
        "peso_inicial_promedio": 1.200,
        "observaciones": "[AUDIT] Lote para flujo de prueba"
    }
    r = requests.post(f"{BASE}/api/v1/lotes/", json=payload_lote, headers=auth_header(token_admin))
    ok_lote = r.status_code == 201
    lote_id = r.json()["id"] if ok_lote else None
    if ok_lote:
        created_resources["lotes"].append(lote_id)
    log_test(5, "FLUJO", "2/6 Creación de Lote", ok_lote, f"lote_id={lote_id}")

    if not lote_id:
        return

    # C. Biometría
    fecha_valida = datetime.now(timezone.utc).isoformat()
    payload_bio = {
        "lote_id": lote_id,
        "fecha_hora": fecha_valida,
        "cantidad_muestra": 50,
        "peso_total_muestra": 2.500,
        "talla_promedio": 12.5,
        "unidad_talla": "cm",
        "observaciones": "[AUDIT] Muestreo inicial"
    }
    r = requests.post(f"{BASE}/api/v1/biometrias/", json=payload_bio, headers=auth_header(token_admin))
    ok_bio = r.status_code == 201
    bio_id = r.json()["id"] if ok_bio else None
    if ok_bio:
        created_resources["biometrias"].append(bio_id)
    log_test(6, "FLUJO", "3/6 Creación de Biometría", ok_bio, f"biometria_id={bio_id}")

    # D. Mortalidad
    payload_mort = {
        "lote_id": lote_id,
        "fecha_hora": fecha_valida,
        "cantidad": 20,
        "causa": "Manejo",
        "observaciones": "[AUDIT] Mortalidad de prueba"
    }
    r = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload_mort, headers=auth_header(token_admin))
    ok_mort = r.status_code == 201
    mort_id = r.json()["id"] if ok_mort else None
    if ok_mort:
        created_resources["mortalidades"].append(mort_id)
    log_test(7, "FLUJO", "4/6 Creación de Mortalidad", ok_mort, f"mortalidad_id={mort_id}")

    # E. Alimentación
    payload_ali = {
        "lote_id": lote_id,
        "producto_id": 1,
        "fecha_hora": fecha_valida,
        "cantidad": 15.000,
        "observaciones": "[AUDIT] Alimentación inicial"
    }
    r = requests.post(f"{BASE}/api/v1/alimentaciones/", json=payload_ali, headers=auth_header(token_admin))
    ok_ali = r.status_code == 201
    ali_id = r.json()["id"] if ok_ali else None
    if ok_ali:
        created_resources["alimentaciones"].append(ali_id)
    log_test(8, "FLUJO", "5/6 Creación de Alimentación", ok_ali, f"alimentacion_id={ali_id}")

    # F. Cosecha
    payload_cos = {
        "lote_id": lote_id,
        "fecha_hora": fecha_valida,
        "cantidad_peces": 500,
        "peso_total": 250.000,
        "peso_promedio": 0.500,
        "observaciones": "[AUDIT] Cosecha parcial"
    }
    r = requests.post(f"{BASE}/api/v1/cosechas/", json=payload_cos, headers=auth_header(token_admin))
    ok_cos = r.status_code == 201
    cos_id = r.json()["id"] if ok_cos else None
    if ok_cos:
        created_resources["cosechas"].append(cos_id)
    log_test(9, "FLUJO", "6/6 Creación de Cosecha", ok_cos, f"cosecha_id={cos_id}")

    # 4. PRUEBA DE REGULA DE CONSISTENCIA TEMPORAL (Fecha anterior a siembra -> 422)
    fecha_invalida = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    r_bio_inv = requests.post(f"{BASE}/api/v1/biometrias/", json={**payload_bio, "fecha_hora": fecha_invalida}, headers=auth_header(token_admin))
    r_mort_inv = requests.post(f"{BASE}/api/v1/mortalidades/", json={**payload_mort, "fecha_hora": fecha_invalida}, headers=auth_header(token_admin))
    r_ali_inv = requests.post(f"{BASE}/api/v1/alimentaciones/", json={**payload_ali, "fecha_hora": fecha_invalida}, headers=auth_header(token_admin))
    r_cos_inv = requests.post(f"{BASE}/api/v1/cosechas/", json={**payload_cos, "fecha_hora": fecha_invalida}, headers=auth_header(token_admin))

    ok_temp = (r_bio_inv.status_code == 422 and r_mort_inv.status_code == 422 and r_ali_inv.status_code == 422 and r_cos_inv.status_code == 422)
    log_test(10, "TEMPORAL", "Validación fecha < fecha_siembra (422) en los 4 módulos", ok_temp)

    # 5. PRUEBA DE POBLACIÓN (Mortalidad acumulada > cantidad_sembrada -> 422)
    payload_mort_exc = {
        "lote_id": lote_id,
        "fecha_hora": fecha_valida,
        "cantidad": 5000, # Excede 2000 sembrados
        "causa": "Prueba exceso"
    }
    r_mort_exc = requests.post(f"{BASE}/api/v1/mortalidades/", json=payload_mort_exc, headers=auth_header(token_admin))
    ok_pobl = r_mort_exc.status_code == 422
    log_test(11, "POBLACION", "Validación Mortalidad acumulada <= cantidad_sembrada (422)", ok_pobl, f"status={r_mort_exc.status_code}")


# ---------------------------------------------------------------------------
# 6. VERIFICACIÓN DE AUDITORÍA EN POSTGRESQL
# ---------------------------------------------------------------------------
def audit_postgresql_audit():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        tablas_revisar = ["estanques", "lotes", "biometrias", "mortalidades", "alimentaciones", "cosechas"]
        todas_registradas = True
        detalles = {}
        for t in tablas_revisar:
            ids = created_resources[t]
            if ids:
                cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE tabla=%s AND registro_id=%s AND accion='INSERT';", (t, ids[0]))
                cnt = cur.fetchone()[0]
                detalles[t] = cnt
                if cnt == 0:
                    todas_registradas = False
        cur.close()
        conn.close()
        log_test(12, "AUDITORIA", "Registro automático INSERT en biofloc.auditoria (6 módulos)", todas_registradas, str(detalles))
    except Exception as e:
        log_test(12, "AUDITORIA", "Error consultando auditoría", False, str(e))


# ---------------------------------------------------------------------------
# 7. ESTRUCTURA Y SCHEMAS EN POSTGRESQL
# ---------------------------------------------------------------------------
def audit_postgresql_structure():
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
        log_test(13, "POSTGRESQL", f"Conteo exacto (42 BASE TABLE + 4 VIEW = 46 Total)", ok, f"BASE TABLE: {base_tables}, VIEW: {views}")
    except Exception as e:
        log_test(13, "POSTGRESQL", "Error consultando estructura", False, str(e))


# ---------------------------------------------------------------------------
# 8. LIMPIEZA DE DATOS TEMPORALES
# ---------------------------------------------------------------------------
def audit_cleanup():
    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        
        # Eliminar en orden de dependencias FK
        for cid in created_resources["cosechas"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='cosechas' AND registro_id=%s;", (cid,))
            cur.execute("DELETE FROM biofloc.cosechas WHERE id=%s;", (cid,))

        for aid in created_resources["alimentaciones"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='alimentaciones' AND registro_id=%s;", (aid,))
            cur.execute("DELETE FROM biofloc.alimentaciones WHERE id=%s;", (aid,))

        for mid in created_resources["mortalidades"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='mortalidades' AND registro_id=%s;", (mid,))
            cur.execute("DELETE FROM biofloc.mortalidades WHERE id=%s;", (mid,))

        for bid in created_resources["biometrias"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='biometrias' AND registro_id=%s;", (bid,))
            cur.execute("DELETE FROM biofloc.biometrias WHERE id=%s;", (bid,))

        for lid in created_resources["lotes"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='lotes' AND registro_id=%s;", (lid,))
            cur.execute("DELETE FROM biofloc.lotes WHERE id=%s;", (lid,))

        for eid in created_resources["estanques"]:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estanques' AND registro_id=%s;", (eid,))
            cur.execute("DELETE FROM biofloc.estanques WHERE id=%s;", (eid,))

        conn.commit()
        cur.close()
        conn.close()
        log_test(14, "LIMPIEZA", "Eliminación completa de datos de prueba temporales", True, f"Recursos limpiados: {created_resources}")
    except Exception as e:
        log_test(14, "LIMPIEZA", "Error durante la limpieza de datos", False, str(e))


def main():
    print("=" * 75)
    print(" AUDITORÍA TÉCNICA INTEGRAL — EJE PRODUCCIÓN (BIOFLOC ERP V1)")
    print("=" * 75)

    audit_health()
    t_admin, t_operario, t_tecnico = audit_security()
    if t_admin:
        audit_flujo_productivo(t_admin)
        audit_postgresql_audit()
        audit_postgresql_structure()
        audit_cleanup()

    print("-" * 75)
    passed = sum(1 for r in audit_results if r[3])
    total = len(audit_results)
    print(f"RESULTADO DE AUDITORÍA: {passed}/{total} PRUEBAS APROBADAS")
    print("=" * 75)

if __name__ == "__main__":
    main()
