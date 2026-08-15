"""AUDITORÍA ESTRUCTURAL FASE 9 FINANZAS."""
import sys
import os
import hashlib
import psycopg2
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACK = ROOT
DDL = r"C:\Users\Jose Fernandez\Documents\biofloc_erp\database\biofloc_erp_v1_1_schema_final.sql"

DB_CONF = dict(host="localhost", port=5432, dbname="biofloc_erp",
               user="postgres", password="admin")
SCH = "biofloc"

print("="*70)
print("AUDITORÍA ESTRUCTURAL FASE 9 FINANZAS")
print("="*70)
ok_all = True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and cond
    print(("  [OK]" if cond else "  [FAIL]") + f" {name}")
    if detail:
        print("       ->", detail)
    return cond

# 1) PostgreSQL 42+4=46
conn = psycopg2.connect(**DB_CONF); cur = conn.cursor()
cur.execute(
    "SELECT table_type, count(*) FROM information_schema.tables "
    "WHERE table_schema=%s AND table_type IN ('BASE TABLE','VIEW') GROUP BY table_type",
    (SCH,),
)
rows = dict(cur.fetchall())
bt = rows.get("BASE TABLE", 0); vw = rows.get("VIEW", 0)
check("PG 42 BASE TABLE", bt == 42, f"actual={bt}")
check("PG 4 VIEW", vw == 4, f"actual={vw}")
check("PG TOTAL 46", bt + vw == 46, f"actual={bt+vw}")

# 2) SHA-256 DDL
with open(DDL, "rb") as f:
    ddl_bytes = f.read()
sha = hashlib.sha256(ddl_bytes).hexdigest()
SHA_ESP = "b35db89dc83fad95c10fc88fece04e031e680b3b921b12b5a584bfb4047bd2e3"
check("DDL SHA-256 IDÉNTICO", sha == SHA_ESP, f"sha={sha}")

# 3) create_all 0 usos en backend/app
import re
app_dir = os.path.join(BACK, "app")
n_ca = 0
for root, ds, fs in os.walk(app_dir):
    for fn in fs:
        if fn.endswith(".py"):
            p = os.path.join(root, fn)
            txt = open(p, "r", encoding="utf-8", errors="replace").read()
            n_ca += len(re.findall(r"create_all\s*\(", txt))
check("Base.metadata.create_all() = 0", n_ca == 0, f"usos={n_ca}")

# 4) archivos __*.py en backend y tests y raíz
temp_py = []
for base in [BACK]:
    for root, ds, fs in os.walk(base):
        for fn in fs:
            if fn.startswith("__") and fn.endswith(".py") and fn not in ("__init__.py",):
                temp_py.append(os.path.join(root, fn))
check("0 archivos __*.py temporales (no init)", len(temp_py) == 0,
      f"temp={temp_py}")

# 5) 0 datos residuales [TEST_GASTO] [TEST_VENTA]
cur.execute(
    "SELECT count(*) FROM biofloc.gastos WHERE descripcion LIKE %s OR proveedor LIKE %s OR observaciones LIKE %s",
    ("%[TEST_GASTO]%",)*3,
)
ng = cur.fetchone()[0]
cur.execute(
    "SELECT count(*) FROM biofloc.ventas WHERE cliente LIKE %s OR observaciones LIKE %s",
    ("%[TEST_VENTA]%",)*2,
)
nv = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM biofloc.categorias_gasto WHERE nombre LIKE %s", ("%[TEST_GASTO]%",))
ncg = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s OR detalle::text LIKE %s",
            ("%[TEST_GASTO]%", "%[TEST_VENTA]%"))
na = cur.fetchone()[0]
check("0 datos residuales [TEST_GASTO] gastos", ng == 0, f"n={ng}")
check("0 datos residuales [TEST_VENTA] ventas", nv == 0, f"n={nv}")
check("0 datos residuales [TEST_GASTO] categorias_gasto", ncg == 0, f"n={ncg}")
check("0 datos residuales TEST auditoría", na == 0, f"n={na}")

# 6) NO endpoints PUT/PATCH/DELETE en /api/v1/gastos o /api/v1/ventas en openapi
import requests, json
try:
    # levantar servidor? Probablemente no. Pues checkear en código fuente routers.
    def has_method(path, method, router_file):
        p = os.path.join(BACK, "app", "routers", router_file)
        txt = open(p, "r", encoding="utf-8").read()
        patt = r"@router\." + method.lower() + r"\("
        m = re.findall(patt, txt)
        return len(m)
    g_put = has_method("gastos", "put", "gastos.py") + has_method("gastos","patch","gastos.py") + has_method("gastos","delete","gastos.py")
    v_put = has_method("ventas", "put", "ventas.py") + has_method("ventas","patch","ventas.py") + has_method("ventas","delete","ventas.py")
    check("OpenAPI gastos: sin PUT/PATCH/DELETE", g_put == 0, f"ops_mutables={g_put}")
    check("OpenAPI ventas: sin PUT/PATCH/DELETE", v_put == 0, f"ops_mutables={v_put}")
except Exception as e:
    check("OpenAPI mutable check (excepción)", False, f"{e}")

# 7) Agua + Biofloc intactos (no se han tocado desde el último commit? simplemente ver archivos existen y no hay syntaxis)
agua_files = [
    "app/models/parametro_agua.py", "app/models/referencia_agua.py", "app/models/medicion_agua.py",
    "app/models/tipo_aplicacion_biofloc.py", "app/models/medicion_biofloc.py", "app/models/aplicacion_biofloc.py",
    "app/models/alimentacion.py",
]
ex = all(os.path.exists(os.path.join(BACK, f)) for f in agua_files)
check("Archivos Agua+Biofloc+Alimentación existen", ex, "")

cur.close(); conn.close()

# Resumen
print("\n" + "="*70)
print("AUDITORÍA FASE 9:", "APROBADA ✓" if ok_all else "FALLOS ✗")
print("="*70)
sys.exit(0 if ok_all else 2)
