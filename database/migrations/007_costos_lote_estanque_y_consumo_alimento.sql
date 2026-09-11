-- Costos operativos: un gasto puede pertenecer directamente a un lote,
-- a un estanque o ser general. Lote y estanque son excluyentes.
ALTER TABLE biofloc.gastos
    ADD COLUMN IF NOT EXISTS estanque_id BIGINT;

ALTER TABLE biofloc.gastos
    ADD CONSTRAINT gastos_estanque_fk
    FOREIGN KEY (estanque_id) REFERENCES biofloc.estanques(id);

ALTER TABLE biofloc.gastos
    ADD CONSTRAINT gastos_destino_check
    CHECK (lote_id IS NULL OR estanque_id IS NULL);

CREATE INDEX IF NOT EXISTS idx_gastos_estanque_fecha
    ON biofloc.gastos (estanque_id, fecha);

INSERT INTO biofloc.categorias_gasto (id, nombre, descripcion, activo)
SELECT COALESCE(MAX(id), 0) + 1,
       'ALEVINOS',
       'Costo de adquisición de alevinos asignado directamente a un lote.',
       TRUE
FROM biofloc.categorias_gasto
WHERE NOT EXISTS (
    SELECT 1 FROM biofloc.categorias_gasto WHERE nombre = 'ALEVINOS'
);
