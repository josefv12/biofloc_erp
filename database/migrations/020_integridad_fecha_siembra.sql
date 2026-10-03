-- Migración 020: una siembra no puede estar en el futuro.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_siembra_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_siembra_no_futura$
BEGIN
    IF NEW.fecha_siembra > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha de siembra no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_siembra_no_futura$;

DROP TRIGGER IF EXISTS trg_validar_fecha_siembra_no_futura ON biofloc.lotes;
CREATE TRIGGER trg_validar_fecha_siembra_no_futura
BEFORE INSERT OR UPDATE OF fecha_siembra ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_siembra_no_futura();

COMMIT;
