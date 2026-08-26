"""Consulta post-migración 6C. Solo lectura."""
from pathlib import Path
import sys

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from env_tests import DB_CONF


def main() -> None:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute("SET search_path TO biofloc, public")
    cur.execute(
        """
        SELECT rp.id, rp.semana_desde, rp.semana_hasta, rp.peso_esperado_g,
               rp.tasa_alimentacion_pct, rp.raciones_min, rp.raciones_max,
               rp.fase, ep.nombre AS etapa, rp.activo
        FROM referencias_produccion rp
        JOIN especies e ON e.id = rp.especie_id
        JOIN etapas_productivas ep ON ep.id = rp.etapa_productiva_id
        WHERE e.nombre_comun = 'Tilapia roja'
          AND rp.activo IS TRUE
        ORDER BY rp.semana_desde, rp.id
        """
    )
    activas = cur.fetchall()
    print(f"ACTIVAS={len(activas)}")
    for row in activas:
        print(row)
    cur.execute(
        """
        SELECT rp.id, rp.semana_desde, rp.semana_hasta, rp.peso_esperado_g,
               rp.tasa_alimentacion_pct, rp.activo
        FROM referencias_produccion rp
        WHERE rp.id IN (204,205,206,207,222,223,224,225,226,227,228,229)
        ORDER BY rp.id
        """
    )
    print("ANTIGUAS")
    for row in cur.fetchall():
        print(row)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
