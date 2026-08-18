-- ============================================================
-- MIGRACIÓN: unidad canónica de masa productiva
-- ============================================================
-- Convención aprobada:
--   g  → peso individual de pez y peso de muestra de biometría
--   kg → peso total de cosecha
--
-- Columnas afectadas (solo renombrado; el tipo NUMERIC no cambia):
--   lotes.peso_inicial_promedio  → lotes.peso_inicial_promedio_g   NUMERIC(10,3)
--   biometrias.peso_total_muestra → biometrias.peso_total_muestra_g NUMERIC(12,3)
--   cosechas.peso_total          → cosechas.peso_total_kg          NUMERIC(12,3)
--   cosechas.peso_promedio       → cosechas.peso_promedio_g        NUMERIC(10,3)
--
-- Los CHECK existentes (>= 0 / > 0) se conservan; solo se renombran para
-- mantener la convención <tabla>_<columna>_check. Lo mismo aplica a los
-- nombres autogenerados de las constraints NOT NULL, que PostgreSQL no
-- renombra al renombrar la columna.
--
-- vista_ultima_biometria se recrea porque CREATE OR REPLACE VIEW no permite
-- renombrar columnas de salida. Ninguna vista depende de ella.
--
-- Compatibilidad de datos: la migración NO convierte valores. Se ejecutó con
-- 0 biometrías, 0 cosechas y 0 lotes con peso inicial no nulo, por lo que no
-- existen valores previos que reinterpretar.
--
-- Idempotente: se puede ejecutar más de una vez sin efecto adicional.
-- ============================================================

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'biofloc' AND table_name = 'lotes'
          AND column_name = 'peso_inicial_promedio'
    ) THEN
        ALTER TABLE biofloc.lotes
            RENAME COLUMN peso_inicial_promedio TO peso_inicial_promedio_g;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'lotes_peso_inicial_promedio_check'
          AND conrelid = 'biofloc.lotes'::regclass
    ) THEN
        ALTER TABLE biofloc.lotes
            RENAME CONSTRAINT lotes_peso_inicial_promedio_check
            TO lotes_peso_inicial_promedio_g_check;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'biofloc' AND table_name = 'biometrias'
          AND column_name = 'peso_total_muestra'
    ) THEN
        ALTER TABLE biofloc.biometrias
            RENAME COLUMN peso_total_muestra TO peso_total_muestra_g;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'biometrias_peso_total_muestra_check'
          AND conrelid = 'biofloc.biometrias'::regclass
    ) THEN
        ALTER TABLE biofloc.biometrias
            RENAME CONSTRAINT biometrias_peso_total_muestra_check
            TO biometrias_peso_total_muestra_g_check;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'biofloc' AND table_name = 'cosechas'
          AND column_name = 'peso_total'
    ) THEN
        ALTER TABLE biofloc.cosechas
            RENAME COLUMN peso_total TO peso_total_kg;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'cosechas_peso_total_check'
          AND conrelid = 'biofloc.cosechas'::regclass
    ) THEN
        ALTER TABLE biofloc.cosechas
            RENAME CONSTRAINT cosechas_peso_total_check
            TO cosechas_peso_total_kg_check;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'biofloc' AND table_name = 'cosechas'
          AND column_name = 'peso_promedio'
    ) THEN
        ALTER TABLE biofloc.cosechas
            RENAME COLUMN peso_promedio TO peso_promedio_g;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'cosechas_peso_promedio_check'
          AND conrelid = 'biofloc.cosechas'::regclass
    ) THEN
        ALTER TABLE biofloc.cosechas
            RENAME CONSTRAINT cosechas_peso_promedio_check
            TO cosechas_peso_promedio_g_check;
    END IF;

    -- PostgreSQL nombra las constraints NOT NULL automáticamente y NO las
    -- renombra al renombrar la columna. Se alinean para que una base migrada
    -- sea idéntica a una creada desde cero con el DDL.
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'biometrias_peso_total_muestra_not_null'
          AND conrelid = 'biofloc.biometrias'::regclass
    ) THEN
        ALTER TABLE biofloc.biometrias
            RENAME CONSTRAINT biometrias_peso_total_muestra_not_null
            TO biometrias_peso_total_muestra_g_not_null;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'cosechas_peso_total_not_null'
          AND conrelid = 'biofloc.cosechas'::regclass
    ) THEN
        ALTER TABLE biofloc.cosechas
            RENAME CONSTRAINT cosechas_peso_total_not_null
            TO cosechas_peso_total_kg_not_null;
    END IF;
END
$$;

COMMENT ON COLUMN biofloc.lotes.peso_inicial_promedio_g IS
    'Peso promedio individual de los peces al momento de la siembra, en gramos (g).';
COMMENT ON COLUMN biofloc.biometrias.peso_total_muestra_g IS
    'Peso total de la muestra biometrada, en gramos (g). peso_total_muestra_g / cantidad_muestra = peso promedio por pez en gramos.';
COMMENT ON COLUMN biofloc.cosechas.peso_total_kg IS
    'Peso total cosechado, en kilogramos (kg).';
COMMENT ON COLUMN biofloc.cosechas.peso_promedio_g IS
    'Peso promedio individual de los peces cosechados, en gramos (g).';

DROP VIEW IF EXISTS biofloc.vista_ultima_biometria;

CREATE VIEW biofloc.vista_ultima_biometria AS
SELECT DISTINCT ON (lote_id)
    lote_id,
    fecha_hora,
    cantidad_muestra,
    peso_total_muestra_g,
    ROUND(
        peso_total_muestra_g / NULLIF(cantidad_muestra, 0),
        3
    ) AS peso_promedio_g
FROM biofloc.biometrias
ORDER BY lote_id, fecha_hora DESC;

COMMIT;
