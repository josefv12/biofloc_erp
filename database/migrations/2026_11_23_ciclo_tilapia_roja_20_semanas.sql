-- Ciclo productivo de tilapia roja: 20 semanas (5 meses).
-- Solo modifica datos de referencias_produccion.
-- No crea, modifica ni elimina funciones, triggers ni procedimientos.
-- Conserva las referencias anteriores como historial inactivo.

BEGIN;
SET LOCAL search_path TO biofloc, public;

DO $preflight$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM especies
        WHERE LOWER(BTRIM(nombre_comun)) = 'tilapia roja'
    ) THEN
        RAISE EXCEPTION 'No existe la especie Tilapia roja; se cancela la migración sin modificar referencias.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM etapas_productivas WHERE nombre = 'Alevinaje')
       OR NOT EXISTS (SELECT 1 FROM etapas_productivas WHERE nombre = 'Preengorde')
       OR NOT EXISTS (SELECT 1 FROM etapas_productivas WHERE nombre = 'Engorde') THEN
        RAISE EXCEPTION 'Faltan etapas Alevinaje, Preengorde o Engorde; se cancela la migración.';
    END IF;
END
$preflight$;

UPDATE referencias_produccion rp
SET activo = FALSE,
    updated_at = NOW(),
    observaciones = CONCAT(COALESCE(rp.observaciones, ''), ' | Reemplazado por curva oficial de 20 semanas.')
FROM especies e
WHERE rp.especie_id = e.id
  AND LOWER(BTRIM(e.nombre_comun)) = 'tilapia roja'
  AND rp.activo IS TRUE;

WITH datos(semana, peso_g, tasa_pct, raciones_min, raciones_max, fase) AS (
    VALUES
        (1, 6, 13.333, 8, 8, 'Inicio'),
        (2, 12, 9.217, 7, 7, 'Inicio'),
        (3, 22, 7.143, 6, 6, 'Inicio'),
        (4, 34, 5.583, 6, 6, 'Inicio'),
        (5, 45, 4.261, 5, 5, 'Levante'),
        (6, 58, 3.596, 5, 5, 'Levante'),
        (7, 72, 3.218, 4, 4, 'Levante'),
        (8, 87, 2.935, 4, 4, 'Levante'),
        (9, 105, 2.868, 4, 4, 'Levante'),
        (10, 125, 2.73, 4, 4, 'Levante'),
        (11, 150, 2.774, 3, 3, 'Engorde'),
        (12, 175, 2.452, 3, 3, 'Engorde'),
        (13, 202, 2.187, 3, 3, 'Engorde'),
        (14, 228, 1.99, 3, 3, 'Engorde'),
        (15, 256, 1.8, 3, 3, 'Engorde'),
        (16, 283, 1.673, 3, 3, 'Engorde'),
        (17, 312, 1.558, 3, 3, 'Engorde'),
        (18, 341, 1.446, 2, 3, 'Engorde'),
        (19, 370, 1.367, 2, 3, 'Engorde'),
        (20, 400, 1.283, 2, 2, 'Engorde')
),
especie_tilapia AS (
    SELECT id AS especie_id
    FROM especies
    WHERE LOWER(BTRIM(nombre_comun)) = 'tilapia roja'
),
etapas AS (
    SELECT
        MAX(id) FILTER (WHERE nombre = 'Alevinaje') AS alevinaje_id,
        MAX(id) FILTER (WHERE nombre = 'Preengorde') AS preengorde_id,
        MAX(id) FILTER (WHERE nombre = 'Engorde') AS engorde_id
    FROM etapas_productivas
),
referencias AS (
    SELECT
        e.especie_id,
        CASE
            WHEN d.semana BETWEEN 1 AND 8 THEN et.alevinaje_id
            WHEN d.semana BETWEEN 9 AND 16 THEN et.preengorde_id
            ELSE et.engorde_id
        END AS etapa_productiva_id,
        d.*
    FROM especie_tilapia e
    CROSS JOIN datos d
    CROSS JOIN etapas et
)
INSERT INTO referencias_produccion (
    especie_id, etapa_productiva_id, semana_desde, semana_hasta,
    peso_esperado_g, tasa_alimentacion_pct, raciones_min, raciones_max,
    fase, observaciones, activo
)
SELECT
    r.especie_id,
    r.etapa_productiva_id,
    r.semana,
    r.semana,
    r.peso_g,
    r.tasa_pct,
    r.raciones_min,
    r.raciones_max,
    r.fase,
    'Curva oficial tilapia roja 20 semanas. Tasa derivada para reproducir el alimento semanal de la tabla base sobre la biomasa de referencia.',
    TRUE
FROM referencias r
WHERE r.etapa_productiva_id IS NOT NULL
ON CONFLICT (especie_id, etapa_productiva_id, semana_desde, semana_hasta)
DO UPDATE SET
    peso_esperado_g = EXCLUDED.peso_esperado_g,
    tasa_alimentacion_pct = EXCLUDED.tasa_alimentacion_pct,
    raciones_min = EXCLUDED.raciones_min,
    raciones_max = EXCLUDED.raciones_max,
    fase = EXCLUDED.fase,
    observaciones = EXCLUDED.observaciones,
    activo = TRUE,
    updated_at = NOW();

COMMIT;
