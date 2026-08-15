"""One-off PostgreSQL introspection for audit report."""
import psycopg2

DB = dict(host="localhost", port=5432, dbname="biofloc_erp", user="postgres", password="admin")

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    print("=== TABLE COUNTS ===")
    cur.execute("""
        SELECT table_type, count(*)
        FROM information_schema.tables
        WHERE table_schema='biofloc'
        GROUP BY table_type ORDER BY table_type;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n=== FKs AGUA+BIOFLOC ===")
    cur.execute("""
        SELECT tc.table_name, tc.constraint_name, ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'biofloc'
          AND tc.table_name IN ('mediciones_agua','mediciones_biofloc',
                                'aplicaciones_biofloc','referencias_agua','parametros_agua')
        ORDER BY tc.table_name, tc.constraint_name;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n=== fk_aplicacion_producto ===")
    cur.execute("""
        SELECT constraint_name, ccu.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type='FOREIGN KEY'
          AND tc.table_schema='biofloc'
          AND tc.constraint_name='fk_aplicacion_producto';
    """)
    print(cur.fetchall())

    print("\n=== INDEXES ===")
    cur.execute("""
        SELECT indexname, tablename
        FROM pg_indexes
        WHERE schemaname='biofloc'
          AND indexname IN (
            'idx_mediciones_agua_lote_fecha',
            'idx_mediciones_agua_parametro',
            'idx_mediciones_biofloc_lote_fecha',
            'idx_aplicaciones_biofloc_lote_fecha'
          )
        ORDER BY indexname;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n=== CHECK CONSTRAINTS ===")
    cur.execute("""
        SELECT table_name, constraint_name
        FROM information_schema.table_constraints
        WHERE constraint_type='CHECK'
          AND table_schema='biofloc'
          AND table_name IN ('mediciones_agua','mediciones_biofloc',
                             'aplicaciones_biofloc','referencias_agua','parametros_agua')
        ORDER BY table_name, constraint_name;
    """)
    for row in cur.fetchall():
        print(row)

    print("\n=== UNIQUE parametros_agua ===")
    cur.execute("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_schema='biofloc' AND table_name='parametros_agua'
        ORDER BY constraint_type, constraint_name;
    """)
    for row in cur.fetchall():
        print(row)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
