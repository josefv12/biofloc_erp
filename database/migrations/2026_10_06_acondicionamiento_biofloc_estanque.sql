-- Acondicionamiento Biofloc previo a la siembra, asociado al estanque y no al lote.
-- Permite preparar el sistema hasta 7 días antes de la siembra prevista.
SET search_path TO biofloc, public;

BEGIN;

CREATE TABLE IF NOT EXISTS acondicionamientos_biofloc_estanque (
  id BIGSERIAL PRIMARY KEY,
  estanque_id BIGINT NOT NULL REFERENCES estanques(id),
  tipo_aplicacion_id BIGINT NOT NULL REFERENCES tipos_aplicacion_biofloc(id),
  producto_id BIGINT NULL REFERENCES productos(id),
  fecha_hora TIMESTAMPTZ NOT NULL,
  fecha_siembra_prevista DATE NOT NULL,
  cantidad NUMERIC(12,4) NULL CHECK (cantidad IS NULL OR cantidad >= 0),
  unidad VARCHAR(30) NULL,
  aireacion_activa BOOLEAN NOT NULL DEFAULT TRUE,
  observaciones TEXT NULL,
  registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_acond_biofloc_estanque_fecha
  ON acondicionamientos_biofloc_estanque (estanque_id, fecha_hora DESC);

CREATE INDEX IF NOT EXISTS idx_acond_biofloc_estanque_siembra
  ON acondicionamientos_biofloc_estanque (estanque_id, fecha_siembra_prevista);

COMMIT;
