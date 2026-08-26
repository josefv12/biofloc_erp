"""Aplica la migración 6C. Solo ALTER/UPDATE/INSERT en referencias_produccion."""
from pathlib import Path
import sys

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from env_tests import DB_CONF

SQL = Path(__file__).resolve().parents[2] / "database" / "migrations" / "2026_08_19_catalogo_productivo_oficial.sql"


def main() -> None:
    sql = SQL.read_text(encoding="utf-8")
    conn = psycopg2.connect(**DB_CONF)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print("OK migracion 6C")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
