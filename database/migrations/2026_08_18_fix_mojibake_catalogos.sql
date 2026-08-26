-- ============================================================
-- MIGRACIÓN: reparar mojibake restante en catálogos
-- ============================================================
-- Origen: el DDL/seeds están en UTF-8 correcto. La carga histórica se
-- hizo con client_encoding distinto de UTF8 (locale Windows 1252), así
-- que los bytes UTF-8 se guardaron como caracteres Latin-1.
--
-- Reparación: convert_from(convert_to(..., LATIN1), UTF8) SOLO en
-- columnas de texto que todavía contienen U+00C3 o U+00C2.
-- No toca filas ya correctas. No reescribe IDs ni FKs.
--
-- Idempotente.
-- ============================================================

BEGIN;
SET LOCAL search_path TO biofloc;
SET LOCAL client_encoding TO 'UTF8';

CREATE OR REPLACE FUNCTION fix_mojibake_utf8(src TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    IF src IS NULL THEN
        RETURN src;
    END IF;
    IF position(chr(195) IN src) = 0
       AND position(chr(194) IN src) = 0 THEN
        RETURN src;
    END IF;
    RETURN convert_from(convert_to(src, 'LATIN1'), 'UTF8');
EXCEPTION
    WHEN OTHERS THEN
        RETURN src;
END;
$$;

UPDATE roles SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE estados_estanque SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE estados_lote SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE parametros_agua
SET nombre = fix_mojibake_utf8(nombre),
    unidad = fix_mojibake_utf8(unidad),
    descripcion = fix_mojibake_utf8(descripcion);
UPDATE tipos_aplicacion_biofloc SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE categorias_inventario SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE unidades
SET nombre = fix_mojibake_utf8(nombre),
    simbolo = fix_mojibake_utf8(simbolo);
UPDATE tipos_movimiento_inventario SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE categorias_gasto SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE tipos_equipo SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE estados_equipo SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE tipos_mantenimiento SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE tipos_alarma SET descripcion = fix_mojibake_utf8(descripcion);
UPDATE niveles_alarma SET nombre = fix_mojibake_utf8(nombre);
UPDATE estados_alarma
SET nombre = fix_mojibake_utf8(nombre),
    descripcion = fix_mojibake_utf8(descripcion);
UPDATE especies
SET nombre_comun = fix_mojibake_utf8(nombre_comun),
    nombre_cientifico = fix_mojibake_utf8(nombre_cientifico);
UPDATE etapas_productivas
SET nombre = fix_mojibake_utf8(nombre),
    descripcion = fix_mojibake_utf8(descripcion);
UPDATE referencias_agua SET observaciones = fix_mojibake_utf8(observaciones);
UPDATE referencias_produccion SET observaciones = fix_mojibake_utf8(observaciones);
UPDATE referencias_biofloc
SET unidad = fix_mojibake_utf8(unidad),
    observaciones = fix_mojibake_utf8(observaciones);

DROP FUNCTION fix_mojibake_utf8(TEXT);

COMMIT;
