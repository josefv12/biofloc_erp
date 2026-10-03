-- Migración 026: ventas y detalles comerciales son históricos e inmutables.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_venta_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_inmutabilidad_venta$
BEGIN
    RAISE EXCEPTION 'La venta histórica % es inmutable; registre una corrección mediante un nuevo documento', OLD.id
        USING ERRCODE='check_violation';
END;
$fn_inmutabilidad_venta$;

DROP TRIGGER IF EXISTS trg_inmutabilidad_ventas ON biofloc.ventas;
CREATE TRIGGER trg_inmutabilidad_ventas
BEFORE UPDATE OR DELETE ON biofloc.ventas
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_venta_historica();

DROP TRIGGER IF EXISTS trg_inmutabilidad_detalles_venta ON biofloc.detalles_venta;
CREATE TRIGGER trg_inmutabilidad_detalles_venta
BEFORE UPDATE OR DELETE ON biofloc.detalles_venta
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_venta_historica();

COMMIT;
