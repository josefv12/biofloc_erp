-- Reparación de acondicionamientos pre-siembra creados antes de asociar la preparación al lote.
-- Los registros históricos pueden tener lote_id NULL porque la migración 2026_10_09
-- se ejecutó antes de que existiera el lote PLANIFICADO.
BEGIN;

SET search_path TO biofloc, public;

UPDATE acondicionamientos_biofloc_estanque a
SET lote_id = l.id
FROM lotes l
JOIN estados_lote e ON e.id = l.estado_id
WHERE a.lote_id IS NULL
  AND a.estanque_id = l.estanque_id
  AND a.fecha_siembra_prevista = l.fecha_siembra
  AND e.nombre IN ('PLANIFICADO', 'ACTIVO');

CREATE INDEX IF NOT EXISTS idx_acond_biofloc_lote_fecha
  ON acondicionamientos_biofloc_estanque(lote_id, fecha_hora);

-- Solo endurecer la restricción cuando todos los históricos hayan quedado reparados.
DO $func$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM acondicionamientos_biofloc_estanque
    WHERE lote_id IS NULL
  ) THEN
    ALTER TABLE acondicionamientos_biofloc_estanque
      ALTER COLUMN lote_id SET NOT NULL;
  END IF;
END
$func$;

COMMIT;
