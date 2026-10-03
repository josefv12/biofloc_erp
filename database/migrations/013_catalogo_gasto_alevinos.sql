-- Migración 013: completa el catálogo de costos directos del lote.
-- El servicio de costos_lote_service clasifica explícitamente ALEVinos.

BEGIN;

INSERT INTO biofloc.categorias_gasto (nombre, descripcion, activo)
SELECT 'ALEVINOS', 'Compra de alevinos y material vivo de siembra', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM biofloc.categorias_gasto WHERE nombre = 'ALEVINOS'
);

COMMIT;
