-- Migración 017: una sola fila de inventario por evento automático.
-- Evita duplicar entradas/salidas para una misma compra, alimentación
-- o aplicación Biofloc.

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mov_inv_referencia_automatica
ON biofloc.movimientos_inventario (referencia_tipo, referencia_id)
WHERE referencia_tipo IN ('DETALLE_COMPRA', 'ALIMENTACION', 'APLICACION_BIOFLOC')
  AND referencia_id IS NOT NULL;

COMMIT;
