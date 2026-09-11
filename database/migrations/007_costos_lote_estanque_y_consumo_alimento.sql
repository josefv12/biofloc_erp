-- Costos operativos: un gasto puede pertenecer directamente a un lote
-- o a un estanque. No se permite asignarlo a ambos al mismo tiempo.
ALTER TABLE biofloc.gastos
    ADD COLUMN IF NOT EXISTS estanque_id BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'gastos_estanque_fk'
          AND conrelid = 'biofloc.gastos'::regclass
    ) THEN
        ALTER TABLE biofloc.gastos
            ADD CONSTRAINT gastos_estanque_fk
            FOREIGN KEY (estanque_id) REFERENCES biofloc.estanques(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'gastos_destino_check'
          AND conrelid = 'biofloc.gastos'::regclass
    ) THEN
        ALTER TABLE biofloc.gastos
            ADD CONSTRAINT gastos_destino_check
            CHECK (lote_id IS NULL OR estanque_id IS NULL);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_gastos_estanque_fecha
    ON biofloc.gastos (estanque_id, fecha);

COMMENT ON COLUMN biofloc.gastos.lote_id IS
    'Costo directamente imputado al lote. Excluyente con estanque_id.';

COMMENT ON COLUMN biofloc.gastos.estanque_id IS
    'Costo imputado al estanque. Puede representar costos compartidos del estanque y es excluyente con lote_id.';
