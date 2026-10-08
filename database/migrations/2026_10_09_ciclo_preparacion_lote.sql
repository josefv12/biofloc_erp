-- Vincula toda la preparación y las mediciones previas a un ciclo productivo (lote).
-- El estanque sigue siendo la unidad física; el lote representa el ciclo.
BEGIN;

-- Acondicionamiento: el lote es el contexto principal del ciclo.
ALTER TABLE biofloc.acondicionamientos_biofloc_estanque
    ADD COLUMN IF NOT EXISTS lote_id BIGINT;

ALTER TABLE biofloc.acondicionamientos_biofloc_estanque
    ADD CONSTRAINT fk_acond_biofloc_lote
    FOREIGN KEY (lote_id) REFERENCES biofloc.lotes(id);

UPDATE biofloc.acondicionamientos_biofloc_estanque a
SET lote_id = l.id
FROM biofloc.lotes l
WHERE a.lote_id IS NULL
  AND a.estanque_id = l.estanque_id
  AND a.fecha_siembra_prevista = l.fecha_siembra
  AND l.estado_id IN (
      SELECT id FROM biofloc.estados_lote WHERE nombre IN ('PLANIFICADO', 'ACTIVO')
  );

CREATE INDEX IF NOT EXISTS idx_acond_biofloc_lote_fecha
    ON biofloc.acondicionamientos_biofloc_estanque(lote_id, fecha_hora);

-- Las mediciones ya no tienen contexto directo de estanque.
-- El estanque se obtiene mediante lote.estanque_id.
ALTER TABLE biofloc.mediciones_agua
    DROP CONSTRAINT IF EXISTS mediciones_agua_contexto_check;

ALTER TABLE biofloc.mediciones_agua
    DROP COLUMN IF EXISTS estanque_id;

ALTER TABLE biofloc.mediciones_agua
    ALTER COLUMN lote_id SET NOT NULL;

ALTER TABLE biofloc.mediciones_biofloc
    DROP CONSTRAINT IF EXISTS mediciones_biofloc_contexto_check;

ALTER TABLE biofloc.mediciones_biofloc
    DROP COLUMN IF EXISTS estanque_id;

ALTER TABLE biofloc.mediciones_biofloc
    ALTER COLUMN lote_id SET NOT NULL;

COMMIT;
