BEGIN;
SET search_path TO biofloc, public;

ALTER TABLE lotes ADD COLUMN IF NOT EXISTS cantidad_prevista INTEGER;

-- Los ciclos históricos ya sembrados conservan su cantidad como prevista y real.
-- Los ciclos PLANIFICADOS pasan a tener 0 peces reales sembrados.
UPDATE lotes l
SET cantidad_prevista = CASE
    WHEN e.nombre = 'PLANIFICADO' THEN l.cantidad_sembrada
    ELSE l.cantidad_sembrada
END
FROM estados_lote e
WHERE e.id = l.estado_id
  AND l.cantidad_prevista IS NULL;

UPDATE lotes l
SET cantidad_sembrada = 0
FROM estados_lote e
WHERE e.id = l.estado_id
  AND e.nombre = 'PLANIFICADO';

UPDATE lotes
SET cantidad_prevista = cantidad_sembrada
WHERE cantidad_prevista IS NULL;

ALTER TABLE lotes ALTER COLUMN cantidad_prevista SET NOT NULL;
ALTER TABLE lotes ALTER COLUMN cantidad_sembrada SET DEFAULT 0;

ALTER TABLE lotes DROP CONSTRAINT IF EXISTS lotes_cantidad_sembrada_check;
ALTER TABLE lotes DROP CONSTRAINT IF EXISTS lotes_cantidad_prevista_check;
ALTER TABLE lotes ADD CONSTRAINT lotes_cantidad_prevista_check CHECK (cantidad_prevista > 0);
ALTER TABLE lotes ADD CONSTRAINT lotes_cantidad_sembrada_check CHECK (cantidad_sembrada >= 0 AND cantidad_sembrada <= cantidad_prevista);

COMMIT;
