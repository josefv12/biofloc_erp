-- Etapa 6C — catálogo productivo oficial (Tilapia roja, 24 semanas exactas).
-- No toca lotes, biometrías, alimentaciones, cosechas, agua, Biofloc ni finanzas.
-- Las filas antiguas se desactivan; no se eliminan.

SET search_path TO biofloc, public;

BEGIN;

ALTER TABLE referencias_produccion
    ADD COLUMN IF NOT EXISTS raciones_min INTEGER,
    ADD COLUMN IF NOT EXISTS raciones_max INTEGER,
    ADD COLUMN IF NOT EXISTS fase VARCHAR(40);

ALTER TABLE referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_raciones_check;
ALTER TABLE referencias_produccion
    ADD CONSTRAINT referencias_produccion_raciones_check
    CHECK (
        raciones_min IS NULL
        OR raciones_min >= 0
    );

ALTER TABLE referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_raciones_rango_check;
ALTER TABLE referencias_produccion
    ADD CONSTRAINT referencias_produccion_raciones_rango_check
    CHECK (
        raciones_min IS NULL
        OR raciones_max IS NULL
        OR raciones_max >= raciones_min
    );

ALTER TABLE referencias_produccion
    DROP CONSTRAINT IF EXISTS referencias_produccion_fase_check;
ALTER TABLE referencias_produccion
    ADD CONSTRAINT referencias_produccion_fase_check
    CHECK (
        fase IS NULL
        OR fase IN ('Inicio', 'Levante', 'Engorde')
    );

COMMENT ON COLUMN referencias_produccion.raciones_min IS
    'Número mínimo de raciones/día. Si igual a raciones_max, es un valor exacto. No guardar promedios.';
COMMENT ON COLUMN referencias_produccion.raciones_max IS
    'Número máximo de raciones/día. Un rango 6–8 se guarda como min=6 max=8.';
COMMENT ON COLUMN referencias_produccion.fase IS
    'Fase de la tabla de alimentación (Inicio/Levante/Engorde). Independiente de etapas_productivas.';

-- Desactivar curvas antiguas de Tilapia roja (ids auditados 204–207 y 222–229)
-- y cualquier otra activa que no sea la fila oficial de una sola semana.
UPDATE referencias_produccion rp
SET activo = FALSE,
    updated_at = NOW()
FROM especies e
WHERE rp.especie_id = e.id
  AND e.nombre_comun = 'Tilapia roja'
  AND rp.activo IS TRUE
  AND (
        rp.id IN (204, 205, 206, 207, 222, 223, 224, 225, 226, 227, 228, 229)
        OR rp.semana_desde <> rp.semana_hasta
        OR COALESCE(rp.observaciones, '') NOT LIKE 'Catálogo oficial Etapa 6C%'
  );

INSERT INTO referencias_produccion (
    especie_id, etapa_productiva_id, semana_desde, semana_hasta,
    peso_esperado_g, tasa_alimentacion_pct, raciones_min, raciones_max, fase,
    observaciones, activo
)
SELECT
    e.id,
    CASE
        WHEN v.semana BETWEEN 1 AND 8 THEN alev.id
        WHEN v.semana BETWEEN 9 AND 16 THEN pre.id
        ELSE eng.id
    END,
    v.semana,
    v.semana,
    v.peso,
    v.tasa,
    v.r_min,
    v.r_max,
    v.fase,
    'Catálogo oficial Etapa 6C. etapa_productiva_id cumple NOT NULL; no equivale a fase.',
    TRUE
FROM especies e
JOIN etapas_productivas alev ON alev.nombre = 'Alevinaje'
JOIN etapas_productivas pre ON pre.nombre = 'Preengorde'
JOIN etapas_productivas eng ON eng.nombre = 'Engorde'
CROSS JOIN (
    VALUES
        (1,  1.5,   10.0, 6, 8, 'Inicio'),
        (2,  3.0,    9.0, 6, 8, 'Inicio'),
        (3,  6.0,    8.0, 6, 8, 'Inicio'),
        (4, 11.5,    7.0, 6, 8, 'Inicio'),
        (5, 18.5,    6.5, 6, 6, 'Inicio'),
        (6, 26.0,    6.0, 6, 6, 'Inicio'),
        (7, 35.0,    5.5, 5, 5, 'Inicio'),
        (8, 45.0,    5.0, 4, 5, 'Inicio'),
        (9, 57.5,    4.5, 4, 4, 'Levante'),
        (10, 75.0,   4.0, 4, 4, 'Levante'),
        (11, 95.0,   3.5, 3, 4, 'Levante'),
        (12, 117.5,  3.2, 3, 4, 'Levante'),
        (13, 142.5,  3.0, 3, 4, 'Levante'),
        (14, 170.0,  2.8, 3, 3, 'Levante'),
        (15, 200.0,  2.6, 3, 3, 'Levante'),
        (16, 232.5,  2.5, 3, 3, 'Levante'),
        (17, 265.0,  2.3, 2, 3, 'Engorde'),
        (18, 297.5,  2.1, 2, 3, 'Engorde'),
        (19, 332.5,  1.9, 2, 3, 'Engorde'),
        (20, 367.5,  1.7, 2, 2, 'Engorde'),
        (21, 402.5,  1.5, 2, 2, 'Engorde'),
        (22, 437.5,  1.3, 2, 2, 'Engorde'),
        (23, 470.0,  1.1, 2, 2, 'Engorde'),
        (24, 500.0,  1.0, 2, 2, 'Engorde')
) AS v(semana, peso, tasa, r_min, r_max, fase)
WHERE e.nombre_comun = 'Tilapia roja'
  AND NOT EXISTS (
      SELECT 1
      FROM referencias_produccion rp
      WHERE rp.especie_id = e.id
        AND rp.activo IS TRUE
        AND rp.semana_desde = v.semana
        AND rp.semana_hasta = v.semana
  );

COMMIT;
