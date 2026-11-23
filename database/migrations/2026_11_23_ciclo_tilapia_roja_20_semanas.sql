-- Ciclo productivo de tilapia roja: 20 semanas (5 meses).
-- Actualiza únicamente datos de referencias_produccion.
-- No crea, modifica ni elimina funciones, triggers ni procedimientos.
-- Conserva las filas históricas de semanas 21-24 desactivándolas.

BEGIN;
SET LOCAL search_path TO biofloc, public;

WITH datos(
    semana, peso_g, tasa_pct, raciones_min, raciones_max, fase
) AS (
    VALUES
        (1, 6.0, 13.333, 8, 8, 'Inicio'),
        (2, 12.0, 9.217, 7, 7, 'Inicio'),
        (3, 22.0, 7.143, 6, 6, 'Inicio'),
        (4, 34.0, 5.583, 6, 6, 'Inicio'),
        (5, 45.0, 4.261, 5, 5, 'Levante'),
        (6, 58.0, 3.596, 5, 5, 'Levante'),
        (7, 72.0, 3.218, 4, 4, 'Levante'),
        (8, 87.0, 2.935, 4, 4, 'Levante'),
        (9, 105.0, 2.868, 4, 4, 'Levante'),
        (10, 125.0, 2.730, 4, 4, 'Levante'),
        (11, 150.0, 2.774, 3, 3, 'Engorde'),
        (12, 175.0, 2.452, 3, 3, 'Engorde'),
        (13, 202.0, 2.187, 3, 3, 'Engorde'),
        (14, 228.0, 1.990, 3, 3, 'Engorde'),
        (15, 256.0, 1.800, 3, 3, 'Engorde'),
        (16, 283.0, 1.673, 3, 3, 'Engorde'),
        (17, 312.0, 1.558, 3, 3, 'Engorde'),
        (18, 341.0, 1.446, 2, 3, 'Engorde'),
        (19, 370.0, 1.367, 2, 3, 'Engorde'),
        (20, 400.0, 1.283, 2, 2, 'Engorde')
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
UPDATE referencias_produccion rp
SET activo = FALSE,
    updated_at = NOW(),
    observaciones = CONCAT(COALESCE(rp.observaciones, ''), ' | Histórico: ciclo anterior de 24 semanas; reemplazado por ciclo de 20 semanas.')
FROM especie_tilapia e
WHERE rp.especie_id = e.especie_id
  AND rp.activo IS TRUE
  AND rp.semana_desde >= 21;

-- Desactivar las referencias activas actuales de tilapia roja.
-- Se conservan como historial; las 20 semanas oficiales se reactivan/upsert abajo.
UPDATE referencias_produccion rp
SET activo = FALSE,
    updated_at = NOW(),
    observaciones = CONCAT(COALESCE(rp.observaciones, ''), ' | Reemplazado por curva oficial de 20 semanas.')
FROM especies e
WHERE rp.especie_id = e.id
  AND LOWER(BTRIM(e.nombre_comun)) = 'tilapia roja'
  AND rp.activo IS TRUE;

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
    'Curva oficial tilapia roja 20 semanas. Tasa derivada para que la ración diaria sobre biomasa de referencia reproduzca el alimento semanal de la tabla base.',
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
