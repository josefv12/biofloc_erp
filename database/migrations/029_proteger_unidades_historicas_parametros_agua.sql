-- ============================================================
-- MIGRACIÓN 029: proteger unidad histórica de parámetros de agua
-- ============================================================
-- Una medición de agua guarda parametro_id, no una copia de la unidad.
-- Por tanto, cambiar parametros_agua.unidad después de registrar mediciones
-- reinterpretaría históricamente todos sus valores.
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_unidad_parametro_agua_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_unidad_parametro_agua_historica$
BEGIN
    IF NEW.unidad IS DISTINCT FROM OLD.unidad
       AND EXISTS (
           SELECT 1
           FROM biofloc.mediciones_agua
           WHERE parametro_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'No se puede cambiar la unidad del parámetro de agua % porque tiene mediciones históricas',
            OLD.id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_unidad_parametro_agua_historica$;

DROP TRIGGER IF EXISTS trg_validar_unidad_parametro_agua_historica
    ON biofloc.parametros_agua;

CREATE TRIGGER trg_validar_unidad_parametro_agua_historica
BEFORE UPDATE OF unidad ON biofloc.parametros_agua
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_unidad_parametro_agua_historica();

COMMIT;
