-- Migración 027: compras y gastos históricos son inmutables.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_financiera_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_inmutabilidad_financiera$
BEGIN
    RAISE EXCEPTION 'El registro financiero histórico % de la tabla % es inmutable', OLD.id, TG_TABLE_NAME
        USING ERRCODE='check_violation';
END;
$fn_inmutabilidad_financiera$;

DROP TRIGGER IF EXISTS trg_inmutabilidad_compras ON biofloc.compras;
CREATE TRIGGER trg_inmutabilidad_compras
BEFORE UPDATE OR DELETE ON biofloc.compras
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_financiera_historica();

DROP TRIGGER IF EXISTS trg_inmutabilidad_gastos ON biofloc.gastos;
CREATE TRIGGER trg_inmutabilidad_gastos
BEFORE UPDATE OR DELETE ON biofloc.gastos
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_financiera_historica();

COMMIT;
