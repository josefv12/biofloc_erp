-- Migración 023: segunda barrera temporal para compras, ventas e inventario.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_comercial_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_comercial_no_futura$
BEGIN
    IF NEW.fecha > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha comercial no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_fecha_comercial_no_futura$;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_movimiento_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_movimiento_no_futura$
BEGIN
    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del movimiento de inventario no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_fecha_movimiento_no_futura$;

DROP TRIGGER IF EXISTS trg_validar_fecha_compra_no_futura ON biofloc.compras;
CREATE TRIGGER trg_validar_fecha_compra_no_futura
BEFORE INSERT OR UPDATE ON biofloc.compras
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_comercial_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_venta_no_futura ON biofloc.ventas;
CREATE TRIGGER trg_validar_fecha_venta_no_futura
BEFORE INSERT OR UPDATE ON biofloc.ventas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_comercial_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_movimiento_no_futura ON biofloc.movimientos_inventario;
CREATE TRIGGER trg_validar_fecha_movimiento_no_futura
BEFORE INSERT OR UPDATE ON biofloc.movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_movimiento_no_futura();

COMMIT;
