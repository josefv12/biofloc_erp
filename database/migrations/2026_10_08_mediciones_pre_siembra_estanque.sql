-- Permite registrar calidad de agua y Biofloc durante la preparación del estanque,
-- antes de que exista un lote. Los registros históricos de lotes se conservan.
BEGIN;

ALTER TABLE biofloc.mediciones_agua
    ADD COLUMN IF NOT EXISTS estanque_id BIGINT;

ALTER TABLE biofloc.mediciones_agua
    ALTER COLUMN lote_id DROP NOT NULL;

ALTER TABLE biofloc.mediciones_agua
    ADD CONSTRAINT fk_mediciones_agua_estanque
    FOREIGN KEY (estanque_id) REFERENCES biofloc.estanques(id);

ALTER TABLE biofloc.mediciones_agua
    DROP CONSTRAINT IF EXISTS mediciones_agua_contexto_check;

ALTER TABLE biofloc.mediciones_agua
    ADD CONSTRAINT mediciones_agua_contexto_check
    CHECK (
        (lote_id IS NOT NULL AND estanque_id IS NULL)
        OR
        (lote_id IS NULL AND estanque_id IS NOT NULL)
    );

CREATE INDEX IF NOT EXISTS idx_mediciones_agua_estanque_fecha
    ON biofloc.mediciones_agua(estanque_id, fecha_hora);

ALTER TABLE biofloc.mediciones_biofloc
    ADD COLUMN IF NOT EXISTS estanque_id BIGINT;

ALTER TABLE biofloc.mediciones_biofloc
    ALTER COLUMN lote_id DROP NOT NULL;

ALTER TABLE biofloc.mediciones_biofloc
    ADD CONSTRAINT fk_mediciones_biofloc_estanque
    FOREIGN KEY (estanque_id) REFERENCES biofloc.estanques(id);

ALTER TABLE biofloc.mediciones_biofloc
    DROP CONSTRAINT IF EXISTS mediciones_biofloc_contexto_check;

ALTER TABLE biofloc.mediciones_biofloc
    ADD CONSTRAINT mediciones_biofloc_contexto_check
    CHECK (
        (lote_id IS NOT NULL AND estanque_id IS NULL)
        OR
        (lote_id IS NULL AND estanque_id IS NOT NULL)
    );

CREATE INDEX IF NOT EXISTS idx_mediciones_biofloc_estanque_fecha
    ON biofloc.mediciones_biofloc(estanque_id, fecha_hora);

COMMIT;
