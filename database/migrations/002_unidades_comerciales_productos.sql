-- Migración 002: unidad comercial y factor de conversión por producto
-- IMPORTANTE: ejecutar en Neon solo después de desplegar el backend compatible.
-- No modifica movimientos, compras, alimentaciones ni datos históricos.

BEGIN;

ALTER TABLE biofloc.productos
    ADD COLUMN IF NOT EXISTS unidad_comercial_id BIGINT;

ALTER TABLE biofloc.productos
    ADD COLUMN IF NOT EXISTS factor_conversion NUMERIC(18,6) NOT NULL DEFAULT 1;

-- Compatibilidad segura para productos existentes:
-- inicialmente la unidad comercial coincide con la unidad interna.
UPDATE biofloc.productos
SET unidad_comercial_id = unidad_id
WHERE unidad_comercial_id IS NULL;

ALTER TABLE biofloc.productos
    ALTER COLUMN unidad_comercial_id SET NOT NULL;

ALTER TABLE biofloc.productos
    ADD CONSTRAINT fk_productos_unidad_comercial
    FOREIGN KEY (unidad_comercial_id) REFERENCES biofloc.unidades(id);

ALTER TABLE biofloc.productos
    ADD CONSTRAINT productos_factor_conversion_check
    CHECK (factor_conversion > 0);

COMMIT;
