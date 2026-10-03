-- Migración 028: un gasto directo de lote no puede preceder su siembra.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_gasto_lote()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_gasto_lote$
DECLARE
    v_fecha_siembra DATE;
BEGIN
    IF NEW.lote_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT l.fecha_siembra
      INTO v_fecha_siembra
      FROM biofloc.lotes l
     WHERE l.id = NEW.lote_id;

    IF v_fecha_siembra IS NULL THEN
        RAISE EXCEPTION 'No existe el lote %', NEW.lote_id
            USING ERRCODE='foreign_key_violation';
    END IF;

    IF NEW.fecha < v_fecha_siembra THEN
        RAISE EXCEPTION 'La fecha del gasto % no puede ser anterior a la siembra del lote %', NEW.fecha, NEW.lote_id
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_fecha_gasto_lote$;

DROP TRIGGER IF EXISTS trg_validar_fecha_gasto_lote ON biofloc.gastos;
CREATE TRIGGER trg_validar_fecha_gasto_lote
BEFORE INSERT OR UPDATE OF fecha, lote_id ON biofloc.gastos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_fecha_gasto_lote();

COMMIT;
