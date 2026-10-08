BEGIN;
SET search_path TO biofloc, public;

ALTER TABLE lotes ADD COLUMN IF NOT EXISTS cantidad_prevista INTEGER;

UPDATE lotes
SET cantidad_prevista = cantidad_sembrada
WHERE cantidad_prevista IS NULL;

-- Primero se elimina la regla histórica que exigía cantidad_sembrada > 0.
-- Esto permite representar correctamente un lote PLANIFICADO sin peces aún consumidos.
ALTER TABLE lotes DROP CONSTRAINT IF EXISTS lotes_cantidad_sembrada_check;
ALTER TABLE lotes DROP CONSTRAINT IF EXISTS lotes_cantidad_prevista_check;

UPDATE lotes l
SET cantidad_sembrada = 0
FROM estados_lote e
WHERE e.id = l.estado_id
  AND e.nombre = 'PLANIFICADO';

ALTER TABLE lotes ALTER COLUMN cantidad_prevista SET NOT NULL;
ALTER TABLE lotes ALTER COLUMN cantidad_sembrada SET DEFAULT 0;

ALTER TABLE lotes
  ADD CONSTRAINT lotes_cantidad_prevista_check
  CHECK (cantidad_prevista > 0);

ALTER TABLE lotes
  ADD CONSTRAINT lotes_cantidad_sembrada_check
  CHECK (cantidad_sembrada >= 0 AND cantidad_sembrada <= cantidad_prevista);

COMMIT;
