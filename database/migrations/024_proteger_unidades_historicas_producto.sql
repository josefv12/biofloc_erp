-- Migración 024: protege unidades históricas de productos con movimientos.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_unidad_producto_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_unidad_producto_historica$
BEGIN
    IF (NEW.unidad_id IS DISTINCT FROM OLD.unidad_id
        OR NEW.unidad_comercial_id IS DISTINCT FROM OLD.unidad_comercial_id
        OR NEW.factor_conversion IS DISTINCT FROM OLD.factor_conversion)
       AND EXISTS (
           SELECT 1 FROM biofloc.movimientos_inventario
           WHERE producto_id = OLD.id
       )
    THEN
        RAISE EXCEPTION 'No se pueden cambiar las unidades o el factor de conversión de un producto con movimientos históricos'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_unidad_producto_historica$;

DROP TRIGGER IF EXISTS trg_validar_unidad_producto_historica ON biofloc.productos;
CREATE TRIGGER trg_validar_unidad_producto_historica
BEFORE UPDATE OF unidad_id, unidad_comercial_id, factor_conversion ON biofloc.productos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_unidad_producto_historica();

COMMIT;
