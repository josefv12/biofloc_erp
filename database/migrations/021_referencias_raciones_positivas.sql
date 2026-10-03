-- Migración 021: raciones diarias estrictamente positivas.
BEGIN;

ALTER TABLE biofloc.referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_raciones_check;
ALTER TABLE biofloc.referencias_produccion
    ADD CONSTRAINT referencias_produccion_raciones_check
    CHECK (raciones_min IS NULL OR raciones_min > 0);

ALTER TABLE biofloc.referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_raciones_rango_check;
ALTER TABLE biofloc.referencias_produccion
    ADD CONSTRAINT referencias_produccion_raciones_rango_check
    CHECK (
        raciones_max IS NULL
        OR (
            raciones_max > 0
            AND (raciones_min IS NULL OR raciones_max >= raciones_min)
        )
    );

COMMIT;
