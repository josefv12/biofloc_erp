-- Migración 022: gastos no pueden registrarse en fechas futuras.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_gasto_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_gasto_no_futuro$
BEGIN
    IF NEW.fecha > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha del gasto no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_gasto_no_futuro$;

DROP TRIGGER IF EXISTS trg_validar_fecha_gasto_no_futura ON biofloc.gastos;
CREATE TRIGGER trg_validar_fecha_gasto_no_futura
BEFORE INSERT OR UPDATE ON biofloc.gastos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_gasto_no_futura();

COMMIT;
