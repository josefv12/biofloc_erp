-- Migración 018: las referencias productivas empiezan en semana 1.
BEGIN;

ALTER TABLE biofloc.referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_semana_desde_check;
ALTER TABLE biofloc.referencias_produccion
    ADD CONSTRAINT referencias_produccion_semana_desde_check
    CHECK (semana_desde >= 1);

ALTER TABLE biofloc.referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_semana_hasta_check;
ALTER TABLE biofloc.referencias_produccion
    ADD CONSTRAINT referencias_produccion_semana_hasta_check
    CHECK (semana_hasta >= semana_desde);

COMMIT;
