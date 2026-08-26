-- ============================================================
-- MIGRACIÓN: referencias_biofloc + corrección de mojibake en catálogos
-- ============================================================
-- Justificación:
--   mediciones_biofloc ya registra volumen_sedimentable y relacion_cn.
--   No existía tabla de rangos/objetivo. El administrador debe poder
--   digitarlos por especie y etapa, sin sembrar valores.
--
-- Indicador:
--   VOLUMEN_SEDIMENTABLE  → sólidos sedimentables de la medición
--   RELACION_CN           → relación C:N de la medición
-- No se inventan otros parámetros científicos.
--
-- Codificación:
--   Corrige texto UTF-8 interpretado dos veces. Solo filas cuyo texto
--   contiene U+00C3 o U+00C2 (marcadores típicos). No toca filas ya
--   correctas. No incrusta esos caracteres en este archivo.
--
-- Idempotente.
-- ============================================================

BEGIN;
SET LOCAL search_path TO biofloc;
SET LOCAL client_encoding TO 'UTF8';

CREATE TABLE IF NOT EXISTS referencias_biofloc (
    id BIGSERIAL PRIMARY KEY,
    especie_id BIGINT NOT NULL REFERENCES especies(id),
    etapa_productiva_id BIGINT NOT NULL REFERENCES etapas_productivas(id),
    indicador VARCHAR(40) NOT NULL,
    valor_minimo NUMERIC(12,4),
    valor_objetivo NUMERIC(12,4),
    valor_maximo NUMERIC(12,4),
    unidad VARCHAR(30),
    observaciones TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (indicador IN ('VOLUMEN_SEDIMENTABLE', 'RELACION_CN')),
    CHECK (
        valor_minimo IS NULL
        OR valor_maximo IS NULL
        OR valor_minimo <= valor_maximo
    ),
    CHECK (
        valor_objetivo IS NULL
        OR valor_minimo IS NULL
        OR valor_objetivo >= valor_minimo
    ),
    CHECK (
        valor_objetivo IS NULL
        OR valor_maximo IS NULL
        OR valor_objetivo <= valor_maximo
    ),
    UNIQUE (especie_id, etapa_productiva_id, indicador)
);

CREATE INDEX IF NOT EXISTS idx_referencias_biofloc_especie_etapa
    ON referencias_biofloc (especie_id, etapa_productiva_id);

COMMENT ON TABLE referencias_biofloc IS
    'Rangos y objetivo de Biofloc por especie y etapa. Los valores los digita el administrador; no hay semilla.';
COMMENT ON COLUMN referencias_biofloc.indicador IS
    'VOLUMEN_SEDIMENTABLE o RELACION_CN, alineado a mediciones_biofloc.';

-- Mojibake: UTF-8 leído como Latin-1 y vuelto a guardar.
UPDATE parametros_agua
SET nombre = convert_from(convert_to(nombre, 'LATIN1'), 'UTF8')
WHERE nombre LIKE '%' || chr(195) || '%' OR nombre LIKE '%' || chr(194) || '%';

UPDATE parametros_agua
SET descripcion = convert_from(convert_to(descripcion, 'LATIN1'), 'UTF8')
WHERE descripcion IS NOT NULL
  AND (descripcion LIKE '%' || chr(195) || '%' OR descripcion LIKE '%' || chr(194) || '%');

UPDATE parametros_agua
SET unidad = convert_from(convert_to(unidad, 'LATIN1'), 'UTF8')
WHERE unidad LIKE '%' || chr(195) || '%' OR unidad LIKE '%' || chr(194) || '%';

COMMIT;
