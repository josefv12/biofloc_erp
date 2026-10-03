-- Migración 025: eventos con trazabilidad de inventario y movimientos históricos son inmutables.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_impedir_modificacion_historico$
BEGIN
    RAISE EXCEPTION 'El registro histórico % de la tabla % es inmutable', OLD.id, TG_TABLE_NAME
        USING ERRCODE='check_violation';
END;
$fn_impedir_modificacion_historico$;

DROP TRIGGER IF EXISTS trg_inmutabilidad_movimientos_inventario ON biofloc.movimientos_inventario;
CREATE TRIGGER trg_inmutabilidad_movimientos_inventario
BEFORE UPDATE OR DELETE ON biofloc.movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();

DROP TRIGGER IF EXISTS trg_inmutabilidad_alimentaciones ON biofloc.alimentaciones;
CREATE TRIGGER trg_inmutabilidad_alimentaciones
BEFORE UPDATE OR DELETE ON biofloc.alimentaciones
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();

DROP TRIGGER IF EXISTS trg_inmutabilidad_aplicaciones_biofloc ON biofloc.aplicaciones_biofloc;
CREATE TRIGGER trg_inmutabilidad_aplicaciones_biofloc
BEFORE UPDATE OR DELETE ON biofloc.aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();

DROP TRIGGER IF EXISTS trg_inmutabilidad_detalles_compra ON biofloc.detalles_compra;
CREATE TRIGGER trg_inmutabilidad_detalles_compra
BEFORE UPDATE OR DELETE ON biofloc.detalles_compra
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();

COMMIT;
