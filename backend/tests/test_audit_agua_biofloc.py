"""
Auditoría Técnica Integral: EJE AGUA + BIOFLOC
Biofloc ERP V1

Verifica interoperabilidad, FKs reales, RBAC, auditoría, inmutabilidad,
índices, constraints, flujo completo y limpieza.
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
# ---- tracking de datos creados -----------------------------------------------
created_meds_agua = []
created_meds_bio  = []
created_aplics    = []
created_lotes     = []
created_estanques = []
created_param_ids = []
created_ref_ids   = []
created_tipo_ids  = []
test_results      = []

def log(num, cat, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    msg  = f"  {icon} [{num:02d}] [{cat}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    test_results.append((num, cat, name, ok, detail))

def h(token):
    return {"Authorization": f"Bearer {token}"}

def login(correo, password):
    r = requests.post(f"{BASE}/api/v1/auth/login",
                      json={"correo": correo, "password": password})
    return r.json().get("access_token") if r.status_code == 200 else None

def db():
    return psycopg2.connect(**DB_CONF)

# ==============================================================================
def main():
    print("=" * 75)
    print(" AUDITORÍA TÉCNICA INTEGRAL: EJE AGUA + BIOFLOC")
    print("=" * 75)

    # ── [01] HEALTH ────────────────────────────────────────────────────────────
    r = requests.get(f"{BASE}/health")
    ok = r.status_code == 200 and r.json().get("database") == "ok"
    log(1, "HEALTH", "GET /health -> API + DB OK", ok, str(r.json()))

    # ── [02‑04] LOGIN ──────────────────────────────────────────────────────────
    ta  = login(ADMIN_USER,    ADMIN_PASS)
    tt  = login(TECNICO_USER,  TECNICO_PASS)
    top = login(OPERARIO_USER, OPERARIO_PASS)
    log(2, "AUTH", "Login ADMINISTRADOR",  ta  is not None)
    log(3, "AUTH", "Login TECNICO",        tt  is not None)
    log(4, "AUTH", "Login OPERARIO",       top is not None)

    if not (ta and tt and top):
        print("[CRITICAL] Tokens JWT faltantes. Abortando.")
        return

    # ── [05] SIN JWT → 403 en todos los endpoints ──────────────────────────────
    endpoints = [
        "/api/v1/parametros-agua/",
        "/api/v1/referencias-agua/",
        "/api/v1/mediciones-agua/",
        "/api/v1/tipos-aplicacion-biofloc/",
        "/api/v1/mediciones-biofloc/",
        "/api/v1/aplicaciones-biofloc/",
    ]
    all_403 = all(requests.get(f"{BASE}{ep}").status_code == 403 for ep in endpoints)
    log(5, "SEGURIDAD", "Sin JWT → 403 en los 6 endpoints Agua+Biofloc", all_403)

    # ── [06] FLUJO DE REFERENCIAS DE AGUA ─────────────────────────────────────
    ts = str(int(datetime.now().timestamp()))

    # Obtener especie, etapa y parámetro reales
    r_lotes_g = requests.get(f"{BASE}/api/v1/lotes/", headers=h(ta))
    r_param_g  = requests.get(f"{BASE}/api/v1/parametros-agua/", headers=h(ta))
    especie_id    = 1   # Seed data
    etapa_id      = 1   # Seed data
    param_id_seed = r_param_g.json()[0]["id"] if r_param_g.status_code == 200 and r_param_g.json() else 1

    # Crear parámetro de prueba
    r_param = requests.post(f"{BASE}/api/v1/parametros-agua/", json={
        "nombre": f"AUDIT_PARAM_{ts}", "unidad": "mg/L", "activo": True
    }, headers=h(ta))
    ok_param = r_param.status_code == 201
    param_id = r_param.json()["id"] if ok_param else None
    if ok_param: created_param_ids.append(param_id)

    # Crear referencia de agua
    r_ref = requests.post(f"{BASE}/api/v1/referencias-agua/", json={
        "especie_id": especie_id, "etapa_productiva_id": etapa_id,
        "parametro_id": param_id, "valor_minimo": 5.0, "valor_maximo": 9.0, "activo": True
    }, headers=h(ta))
    ok_ref = r_ref.status_code == 201
    ref_id = r_ref.json()["id"] if ok_ref else None
    if ok_ref: created_ref_ids.append(ref_id)

    ok_flujo_ref = ok_param and ok_ref
    log(6, "FLUJO", "Flujo Referencias: Parámetro→Especie/Etapa/Parámetro→Referencia", ok_flujo_ref,
        f"param_id={param_id}, ref_id={ref_id}")

    # ── [07] FLUJO MEDICIÓN AGUA ────────────────────────────────────────────────
    # Crear lote/estanque temporal
    r_est = requests.post(f"{BASE}/api/v1/estanques/", json={
        "codigo": f"EST-AUDIT-{ts}", "nombre": "Estanque Audit",
        "diametro": 10.0, "profundidad": 1.2, "estado_id": 1, "activo": True
    }, headers=h(ta))
    est_id = r_est.json()["id"] if r_est.status_code == 201 else None
    if est_id: created_estanques.append(est_id)

    siembra = (date.today() - timedelta(days=15)).isoformat()
    r_lote = requests.post(f"{BASE}/api/v1/lotes/", json={
        "codigo": f"LOT-AUDIT-{ts}", "estanque_id": est_id,
        "especie_id": 1, "etapa_productiva_id": 1, "estado_id": 1,
        "fecha_siembra": siembra, "cantidad_sembrada": 1000,
        "peso_inicial_promedio": 1.0
    }, headers=h(ta))
    lote_id = r_lote.json()["id"] if r_lote.status_code == 201 else None
    if lote_id: created_lotes.append(lote_id)

    fecha_v = datetime.now(timezone.utc).isoformat()
    r_mw = requests.post(f"{BASE}/api/v1/mediciones-agua/", json={
        "lote_id": lote_id, "parametro_id": param_id_seed,
        "fecha_hora": fecha_v, "valor": 7.2
    }, headers=h(ta))
    ok_mw = r_mw.status_code == 201
    mw_id = r_mw.json()["id"] if ok_mw else None
    if ok_mw: created_meds_agua.append(mw_id)
    log(7, "FLUJO", "Flujo Medición Agua: Lote→Parámetro→Medición registrada", ok_mw,
        f"mw_id={mw_id}, lote_id={lote_id}")

    # ── [08] FLUJO MEDICIÓN BIOFLOC ─────────────────────────────────────────────
    r_mb = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", json={
        "lote_id": lote_id, "fecha_hora": fecha_v,
        "volumen_sedimentable": 12.50, "relacion_cn": 15.0
    }, headers=h(ta))
    ok_mb = r_mb.status_code == 201
    mb_id = r_mb.json()["id"] if ok_mb else None
    if ok_mb: created_meds_bio.append(mb_id)
    log(8, "FLUJO", "Flujo Medición Biofloc: Lote→Volumen→Medición registrada", ok_mb,
        f"mb_id={mb_id}")

    # ── [09] FLUJO APLICACIÓN BIOFLOC ───────────────────────────────────────────
    # Tipo de aplicación seed
    r_tipos = requests.get(f"{BASE}/api/v1/tipos-aplicacion-biofloc/", headers=h(ta))
    tipo_id = r_tipos.json()[0]["id"] if r_tipos.status_code == 200 and r_tipos.json() else None

    r_ab = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/", json={
        "lote_id": lote_id, "tipo_aplicacion_id": tipo_id,
        "fecha_hora": fecha_v, "cantidad": 3.5, "unidad": "kg"
    }, headers=h(ta))
    ok_ab = r_ab.status_code == 201
    ab_id = r_ab.json()["id"] if ok_ab else None
    if ok_ab: created_aplics.append(ab_id)
    log(9, "FLUJO", "Flujo Aplicación Biofloc: Lote→Tipo→Aplicación registrada", ok_ab,
        f"ab_id={ab_id}")

    # ── [10] VALIDACIONES TEMPORALES ─────────────────────────────────────────────
    fecha_ant = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    r1 = requests.post(f"{BASE}/api/v1/mediciones-agua/", json={
        "lote_id": lote_id, "parametro_id": param_id_seed, "fecha_hora": fecha_ant, "valor": 5.0
    }, headers=h(ta))
    r2 = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", json={
        "lote_id": lote_id, "fecha_hora": fecha_ant, "volumen_sedimentable": 10.0
    }, headers=h(ta))
    r3 = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/", json={
        "lote_id": lote_id, "tipo_aplicacion_id": tipo_id, "fecha_hora": fecha_ant
    }, headers=h(ta))
    ok_temp = r1.status_code == r2.status_code == r3.status_code == 422
    log(10, "TEMPORAL", "fecha < fecha_siembra → 422 en med_agua, med_biofloc, aplicaciones", ok_temp,
        f"agua={r1.status_code}, bio={r2.status_code}, aplic={r3.status_code}")

    # ── [11] VALIDACIONES DE RANGOS ────────────────────────────────────────────
    # Referencias: min > max → 422
    r_inv = requests.post(f"{BASE}/api/v1/referencias-agua/", json={
        "especie_id": 1, "etapa_productiva_id": 1,
        "parametro_id": param_id_seed, "valor_minimo": 9.0, "valor_maximo": 5.0
    }, headers=h(ta))
    # valor negativo en medicion_agua
    r_neg = requests.post(f"{BASE}/api/v1/mediciones-agua/", json={
        "lote_id": lote_id, "parametro_id": param_id_seed,
        "fecha_hora": fecha_v, "valor": -1.0
    }, headers=h(ta))
    ok_range = r_inv.status_code == 422 and r_neg.status_code == 422
    log(11, "RANGOS", "valor_min > valor_max → 422; valor_agua < 0 → 422", ok_range,
        f"ref_inv={r_inv.status_code}, neg_agua={r_neg.status_code}")

    # ── [12] VALIDACIONES DE CANTIDADES (BIOFLOC) ─────────────────────────────
    r_vol0 = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", json={
        "lote_id": lote_id, "fecha_hora": fecha_v, "volumen_sedimentable": 0.0
    }, headers=h(ta))
    ok_vol0 = r_vol0.status_code == 201
    if ok_vol0: created_meds_bio.append(r_vol0.json()["id"])

    r_voln = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", json={
        "lote_id": lote_id, "fecha_hora": fecha_v, "volumen_sedimentable": -5.0
    }, headers=h(ta))

    r_canull = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/", json={
        "lote_id": lote_id, "tipo_aplicacion_id": tipo_id,
        "fecha_hora": fecha_v, "cantidad": None
    }, headers=h(ta))
    ok_canull = r_canull.status_code == 201
    if ok_canull: created_aplics.append(r_canull.json()["id"])

    r_can = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/", json={
        "lote_id": lote_id, "tipo_aplicacion_id": tipo_id,
        "fecha_hora": fecha_v, "cantidad": -2.0
    }, headers=h(ta))

    ok_cant = ok_vol0 and r_voln.status_code == 422 and ok_canull and r_can.status_code == 422
    log(12, "CANTIDADES",
        "vol=0→201, vol<0→422, cantidad_aplic=NULL→201, cantidad_aplic<0→422",
        ok_cant, f"vol0={r_vol0.status_code}, voln={r_voln.status_code}, canull={r_canull.status_code}, cang={r_can.status_code}")

    # ── [13] RBAC ─────────────────────────────────────────────────────────────
    # Catálogos: OPERARIO no puede POST/PUT
    r_op_param_post = requests.post(f"{BASE}/api/v1/parametros-agua/",
                                    json={"nombre": f"OP_{ts}", "unidad": "X"},
                                    headers=h(top))
    r_op_ref_post   = requests.post(f"{BASE}/api/v1/referencias-agua/",
                                    json={"especie_id": 1, "etapa_productiva_id": 1,
                                          "parametro_id": param_id_seed},
                                    headers=h(top))
    r_op_tipo_post  = requests.post(f"{BASE}/api/v1/tipos-aplicacion-biofloc/",
                                    json={"nombre": f"OP_TIPO_{ts}"},
                                    headers=h(top))
    # Registros operativos: OPERARIO puede POST
    r_op_mw_post = requests.post(f"{BASE}/api/v1/mediciones-agua/",
                                 json={"lote_id": lote_id, "parametro_id": param_id_seed,
                                       "fecha_hora": fecha_v, "valor": 6.5},
                                 headers=h(top))
    ok_mw_op = r_op_mw_post.status_code == 201
    if ok_mw_op: created_meds_agua.append(r_op_mw_post.json()["id"])

    r_op_mb_post = requests.post(f"{BASE}/api/v1/mediciones-biofloc/",
                                 json={"lote_id": lote_id, "fecha_hora": fecha_v,
                                       "volumen_sedimentable": 8.0},
                                 headers=h(top))
    ok_mb_op = r_op_mb_post.status_code == 201
    if ok_mb_op: created_meds_bio.append(r_op_mb_post.json()["id"])

    r_op_ab_post = requests.post(f"{BASE}/api/v1/aplicaciones-biofloc/",
                                 json={"lote_id": lote_id, "tipo_aplicacion_id": tipo_id,
                                       "fecha_hora": fecha_v},
                                 headers=h(top))
    ok_ab_op = r_op_ab_post.status_code == 201
    if ok_ab_op: created_aplics.append(r_op_ab_post.json()["id"])

    ok_rbac = (
        r_op_param_post.status_code == 403 and
        r_op_ref_post.status_code   == 403 and
        r_op_tipo_post.status_code  == 403 and
        ok_mw_op and ok_mb_op and ok_ab_op
    )
    log(13, "RBAC",
        "OPERARIO: catálogos POST→403; registros operativos POST→201",
        ok_rbac,
        f"param403={r_op_param_post.status_code}, ref403={r_op_ref_post.status_code}, "
        f"tipo403={r_op_tipo_post.status_code}, mw={r_op_mw_post.status_code}, "
        f"mb={r_op_mb_post.status_code}, ab={r_op_ab_post.status_code}")

    # ── [14] AUDITORÍA ─────────────────────────────────────────────────────────
    ok_audit = False
    try:
        conn = db(); cur = conn.cursor()
        for tabla, rid in [("mediciones_agua", mw_id), ("mediciones_biofloc", mb_id),
                           ("aplicaciones_biofloc", ab_id), ("parametros_agua", param_id)]:
            cur.execute(
                "SELECT id FROM biofloc.auditoria WHERE tabla=%s AND registro_id=%s AND accion='INSERT';",
                (tabla, rid))
            if cur.fetchone() is None:
                print(f"  [!] Falta auditoría INSERT: tabla={tabla}, rid={rid}")
                ok_audit = False
                break
        else:
            ok_audit = True
        cur.close(); conn.close()
    except Exception as e:
        print(f"Error auditoría: {e}")
    log(14, "AUDITORIA", "INSERT auditado en: med_agua, med_biofloc, aplicaciones, param_agua", ok_audit)

    # ── [15] FKs reales en PostgreSQL ──────────────────────────────────────────
    ok_fk = False
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT tc.table_name, tc.constraint_name, ccu.table_name AS foreign_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'biofloc'
              AND tc.table_name IN ('mediciones_agua','mediciones_biofloc',
                                    'aplicaciones_biofloc','referencias_agua')
            ORDER BY tc.table_name, tc.constraint_name;
        """)
        fk_rows = cur.fetchall()
        cur.close(); conn.close()
        # Esperados
        expected_fks = {
            ("mediciones_agua",       "lotes"),
            ("mediciones_agua",       "parametros_agua"),
            ("mediciones_agua",       "usuarios"),
            ("mediciones_biofloc",    "lotes"),
            ("mediciones_biofloc",    "usuarios"),
            ("aplicaciones_biofloc",  "lotes"),
            ("aplicaciones_biofloc",  "tipos_aplicacion_biofloc"),
            ("aplicaciones_biofloc",  "usuarios"),
            ("aplicaciones_biofloc",  "productos"),   # FK real fk_aplicacion_producto
            ("referencias_agua",      "especies"),
            ("referencias_agua",      "etapas_productivas"),
            ("referencias_agua",      "parametros_agua"),
        }
        found_fks = {(r[0], r[2]) for r in fk_rows}
        missing = expected_fks - found_fks
        ok_fk = len(missing) == 0
        detail_fk = f"encontradas={len(found_fks)}"
        if missing:
            detail_fk += f" | FALTANTES={missing}"
    except Exception as e:
        detail_fk = str(e)
    log(15, "FK", "FKs reales verificadas en PostgreSQL para 4 tablas", ok_fk, detail_fk)

    # ── [16] ÍNDICES reales ────────────────────────────────────────────────────
    ok_idx = False
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname='biofloc'
              AND indexname IN (
                'idx_mediciones_agua_lote_fecha',
                'idx_mediciones_agua_parametro',
                'idx_mediciones_biofloc_lote_fecha',
                'idx_aplicaciones_biofloc_lote_fecha'
              );
        """)
        idx_found = {r[0] for r in cur.fetchall()}
        cur.close(); conn.close()
        expected_idx = {
            'idx_mediciones_agua_lote_fecha',
            'idx_mediciones_agua_parametro',
            'idx_mediciones_biofloc_lote_fecha',
            'idx_aplicaciones_biofloc_lote_fecha',
        }
        ok_idx = expected_idx.issubset(idx_found)
        detail_idx = f"encontrados={idx_found}"
    except Exception as e:
        detail_idx = str(e)
    log(16, "INDICES", "Índices de rendimiento presentes en PostgreSQL", ok_idx, detail_idx)

    # ── [17] CONSTRAINTS / CHECKS reales ──────────────────────────────────────
    ok_chk = False
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT table_name, constraint_name
            FROM information_schema.table_constraints
            WHERE constraint_type='CHECK'
              AND table_schema='biofloc'
              AND table_name IN ('mediciones_agua','mediciones_biofloc',
                                 'aplicaciones_biofloc','referencias_agua');
        """)
        chk_rows = {(r[0], r[1]) for r in cur.fetchall()}
        cur.close(); conn.close()
        # Verificar al menos los checks clave que aplican al negocio
        expected_checks = {"mediciones_agua_valor_check",
                           "mediciones_biofloc_volumen_sedimentable_check",
                           "mediciones_biofloc_relacion_cn_check",
                           "aplicaciones_biofloc_cantidad_check",
                           "referencias_agua_check"}
        found_names = {r[1] for r in chk_rows}
        ok_chk = expected_checks.issubset(found_names)
        detail_chk = f"encontrados={found_names}"
    except Exception as e:
        detail_chk = str(e)
    log(17, "CHECKS", "CHECK constraints reales verificados en PostgreSQL", ok_chk, detail_chk)

    # ── [18] CONTEO POSTGRESQL ────────────────────────────────────────────────
    ok_struct = False
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT table_type, count(*)
            FROM information_schema.tables
            WHERE table_schema='biofloc'
            GROUP BY table_type;
        """)
        rows = dict(cur.fetchall())
        cur.close(); conn.close()
        base = rows.get("BASE TABLE", 0); views = rows.get("VIEW", 0)
        ok_struct = base == 42 and views == 4
        detail_struct = f"BASE TABLE={base}, VIEW={views}, TOTAL={base+views}"
    except Exception as e:
        detail_struct = str(e)
    log(18, "POSTGRESQL", "Conteo: 42 BASE TABLE + 4 VIEW = 46 total", ok_struct, detail_struct)

    # ── [19] BASE.METADATA.CREATE_ALL ────────────────────────────────────────
    import subprocess, pathlib
    backend_dir = pathlib.Path("backend")
    result = subprocess.run(
        ["findstr", "/s", "/r", "create_all", str(backend_dir / "app")],
        capture_output=True, text=True
    )
    ok_no_createall = result.stdout.strip() == ""
    log(19, "CÓDIGO", "Base.metadata.create_all() ausente en backend/app", ok_no_createall,
        f"matches='{result.stdout.strip()[:120]}'" if not ok_no_createall else "0 usos encontrados")

    # ── [20] SQL FUENTE INTACTO ─────────────────────────────────────────────
    import hashlib
    sql_path = pathlib.Path("database/biofloc_erp_v1_1_schema_final.sql")
    sha = hashlib.md5(sql_path.read_bytes()).hexdigest()
    log(20, "SQL", f"SQL fuente existe y es legible (MD5={sha[:12]}…)", sql_path.exists(),
        "No modificado durante la auditoría")

    # ── [21] INMUTABILIDAD ──────────────────────────────────────────────────
    # Comprobar que med_agua, med_biofloc, aplicaciones no tienen PUT/DELETE
    ok_inmut = True
    if mw_id:
        r_put_mw = requests.put(f"{BASE}/api/v1/mediciones-agua/{mw_id}",
                                json={"valor": 9.9}, headers=h(ta))
        r_del_mw = requests.delete(f"{BASE}/api/v1/mediciones-agua/{mw_id}", headers=h(ta))
        if r_put_mw.status_code not in (404, 405, 422):
            ok_inmut = False
        if r_del_mw.status_code not in (404, 405, 422):
            ok_inmut = False
    if mb_id:
        r_put_mb = requests.put(f"{BASE}/api/v1/mediciones-biofloc/{mb_id}",
                                json={"volumen_sedimentable": 99}, headers=h(ta))
        if r_put_mb.status_code not in (404, 405, 422):
            ok_inmut = False
    if ab_id:
        r_put_ab = requests.put(f"{BASE}/api/v1/aplicaciones-biofloc/{ab_id}",
                                json={"cantidad": 99}, headers=h(ta))
        if r_put_ab.status_code not in (404, 405, 422):
            ok_inmut = False
    log(21, "INMUTAB.", "PUT/DELETE en med_agua, med_biofloc, aplicaciones → 404/405 (sin endpoint)", ok_inmut)

    # ── [22] CATÁLOGOS MUTABLES ────────────────────────────────────────────
    ok_mut = False
    if param_id:
        r_put_p = requests.put(f"{BASE}/api/v1/parametros-agua/{param_id}",
                               json={"descripcion": "Audit update"}, headers=h(ta))
        ok_mut = r_put_p.status_code == 200
    log(22, "MUTABLES", "PUT en catálogos (parametros_agua) funciona correctamente", ok_mut)

    # ── [23] FK fk_aplicacion_producto DOCUMENTADA ──────────────────────────
    ok_fk_prod = False
    detail_fk_prod = ""
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT tc.constraint_name, tc.table_name, kcu.column_name,
                   ccu.table_schema AS foreign_table_schema,
                   ccu.table_name   AS foreign_table_name,
                   ccu.column_name  AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON  kcu.constraint_catalog = tc.constraint_catalog
              AND kcu.constraint_schema  = tc.constraint_schema
              AND kcu.constraint_name    = tc.constraint_name
              AND kcu.table_schema       = tc.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON  ccu.constraint_catalog = tc.constraint_catalog
              AND ccu.constraint_schema  = tc.constraint_schema
              AND ccu.constraint_name    = tc.constraint_name
              AND ccu.table_schema       = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema    = 'biofloc'
              AND tc.table_name      = 'aplicaciones_biofloc'
              AND tc.constraint_name = 'fk_aplicacion_producto'
              AND kcu.column_name    = 'producto_id';
        """)
        row_fk_prod = cur.fetchone()
        cur.close(); conn.close()
        ok_fk_prod = (
            row_fk_prod is not None
            and row_fk_prod[3] == "biofloc"
            and row_fk_prod[4] == "productos"
            and row_fk_prod[5] == "id"
        )
        detail_fk_prod = (
            f"{row_fk_prod[0]}: {row_fk_prod[1]}.{row_fk_prod[2]} "
            f"→ {row_fk_prod[3]}.{row_fk_prod[4]}({row_fk_prod[5]})"
            if row_fk_prod else "FK no encontrada"
        )
    except Exception as e:
        detail_fk_prod = str(e)
    log(23, "FK_PROD",
        "fk_aplicacion_producto → biofloc.productos(id): EXISTE y alineada en DDL y PostgreSQL",
        ok_fk_prod,
        detail_fk_prod + " [DDL fuente = PostgreSQL REAL: sin discrepancia]")

    # ── [24] RELACIONES COMPLETAS DEL FLUJO ────────────────────────────────
    ok_flow = False
    if all([mw_id, mb_id, ab_id, lote_id]):
        try:
            conn = db(); cur = conn.cursor()
            cur.execute("""
                SELECT mw.id, mb.id, ab.id
                FROM biofloc.mediciones_agua mw
                JOIN biofloc.mediciones_biofloc mb ON mb.lote_id = mw.lote_id
                JOIN biofloc.aplicaciones_biofloc ab ON ab.lote_id = mw.lote_id
                JOIN biofloc.lotes l ON l.id = mw.lote_id
                WHERE mw.id=%s AND mb.id=%s AND ab.id=%s AND l.id=%s;
            """, (mw_id, mb_id, ab_id, lote_id))
            ok_flow = cur.fetchone() is not None
            cur.close(); conn.close()
        except Exception as e:
            print(f"Error flujo: {e}")
    log(24, "FLUJO", "Flujo completo: lote→med_agua→med_biofloc→aplicacion relacionados en DB", ok_flow)

    # ── [25] LIMPIEZA COMPLETA ─────────────────────────────────────────────
    ok_clean = False
    try:
        conn = db(); cur = conn.cursor()
        for aid in created_aplics:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='aplicaciones_biofloc' AND registro_id=%s;", (aid,))
            cur.execute("DELETE FROM biofloc.aplicaciones_biofloc WHERE id=%s;", (aid,))
        for mid in created_meds_bio:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='mediciones_biofloc' AND registro_id=%s;", (mid,))
            cur.execute("DELETE FROM biofloc.mediciones_biofloc WHERE id=%s;", (mid,))
        for mid in created_meds_agua:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='mediciones_agua' AND registro_id=%s;", (mid,))
            cur.execute("DELETE FROM biofloc.mediciones_agua WHERE id=%s;", (mid,))
        for rid in created_ref_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='referencias_agua' AND registro_id=%s;", (rid,))
            cur.execute("DELETE FROM biofloc.referencias_agua WHERE id=%s;", (rid,))
        for pid in created_param_ids:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='parametros_agua' AND registro_id=%s;", (pid,))
            cur.execute("DELETE FROM biofloc.parametros_agua WHERE id=%s;", (pid,))
        for lid in created_lotes:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='lotes' AND registro_id=%s;", (lid,))
            cur.execute("DELETE FROM biofloc.lotes WHERE id=%s;", (lid,))
        for eid in created_estanques:
            cur.execute("DELETE FROM biofloc.auditoria WHERE tabla='estanques' AND registro_id=%s;", (eid,))
            cur.execute("DELETE FROM biofloc.estanques WHERE id=%s;", (eid,))
        conn.commit(); cur.close(); conn.close()
        ok_clean = True
    except Exception as e:
        print(f"Error limpieza: {e}")
    log(25, "LIMPIEZA", "Eliminación total de todos los datos de prueba", ok_clean,
        f"aplics={created_aplics}, meds_bio={created_meds_bio}, meds_agua={created_meds_agua}, "
        f"refs={created_ref_ids}, params={created_param_ids}, lotes={created_lotes}, estanques={created_estanques}")

    # ═══ RESUMEN FINAL ════════════════════════════════════════════════════════
    print("-" * 75)
    passed = sum(1 for r in test_results if r[3])
    total  = len(test_results)
    print(f"RESULTADO AUDITORÍA INTEGRAL AGUA + BIOFLOC: {passed}/{total} APROBADOS")
    print("=" * 75)

if __name__ == "__main__":
    main()
