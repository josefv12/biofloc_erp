-- Migración 011: trazabilidad 1:1 de movimientos automáticos de inventario.
-- Una alimentación o aplicación Biofloc que consume inventario debe generar
-- como máximo un movimiento de inventario asociado al registro origen.
-- Los movimientos manuales sin referencia no se ven afectados.

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_movimientos_inventario_alimentacion
    ON biofloc.movimientos_inventario (referencia_tipo, referencia_id)
    WHERE referencia_tipo = 'ALIMENTACION'
      AND referencia_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_movimientos_inventario_aplicacion_biofloc
    ON biofloc.movimientos_inventario (referencia_tipo, referencia_id)
    WHERE referencia_tipo = 'APLICACION_BIOFLOC'
      AND referencia_id IS NOT NULL;

COMMIT;
