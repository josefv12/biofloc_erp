-- ============================================================
-- MIGRACIÓN 031: mediciones de agua solo contra parámetros activos
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_parametro_agua_activo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_parametro_agua_activo$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM biofloc.parametros_agua
        WHERE id = NEW.parametro_id
          AND activo = TRUE
    ) THEN
        RAISE EXCEPTION
            'El parámetro de agua % está inactivo y no admite nuevas mediciones',
            NEW.parametro_id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_parametro_agua_activo$;

DROP TRIGGER IF EXISTS trg_validar_parametro_agua_activo
    ON biofloc.mediciones_agua;

CREATE TRIGGER trg_validar_parametro_agua_activo
BEFORE INSERT OR UPDATE OF parametro_id ON biofloc.mediciones_agua
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_parametro_agua_activo();

COMMIT;
