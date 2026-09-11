-- Migración 004: integridad comercial y protección de unidades.
-- Idempotente y segura de ejecutar más de una vez.
-- Se evita dollar-quoting para compatibilidad con ejecutores que separan $$.

BEGIN;

-- El esquema base ya crea idx_detalles_venta_lote sobre lote_id.
-- La limpieza del índice duplicado existente se gestiona por separado.

CREATE OR REPLACE FUNCTION biofloc.validar_disponibilidad_venta()
RETURNS TRIGGER
LANGUAGE plpgsql
AS '
DECLARE
    v_cosechado NUMERIC(18,3);
    v_vendido NUMERIC(18,3);
    v_disponible NUMERIC(18,3);
BEGIN
    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION ''La cantidad de venta debe ser mayor que cero''
            USING ERRCODE = ''check_violation'';
    END IF;

    PERFORM 1
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION ''Lote % no existe'', NEW.lote_id
            USING ERRCODE = ''foreign_key_violation'';
    END IF;

    SELECT COALESCE(SUM(peso_total_kg), 0)
      INTO v_cosechado
      FROM biofloc.cosechas
     WHERE lote_id = NEW.lote_id;

    SELECT COALESCE(SUM(cantidad), 0)
      INTO v_vendido
      FROM biofloc.detalles_venta
     WHERE lote_id = NEW.lote_id;

    v_disponible := GREATEST(v_cosechado - v_vendido, 0);

    IF NEW.cantidad > v_disponible THEN
        RAISE EXCEPTION
            ''Biomasa insuficiente para la venta del lote %. Disponible: % kg, solicitado: % kg'',
            NEW.lote_id, v_disponible, NEW.cantidad
            USING ERRCODE = ''check_violation'';
    END IF;

    RETURN NEW;
END;
';

DROP TRIGGER IF EXISTS trg_validar_disponibilidad_venta
ON biofloc.detalles_venta;

CREATE TRIGGER trg_validar_disponibilidad_venta
BEFORE INSERT ON biofloc.detalles_venta
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_disponibilidad_venta();

CREATE OR REPLACE FUNCTION biofloc.proteger_unidades_producto_con_historial()
RETURNS TRIGGER
LANGUAGE plpgsql
AS '
BEGIN
    IF (NEW.unidad_id IS DISTINCT FROM OLD.unidad_id
        OR NEW.unidad_comercial_id IS DISTINCT FROM OLD.unidad_comercial_id
        OR NEW.factor_conversion IS DISTINCT FROM OLD.factor_conversion)
       AND EXISTS (
           SELECT 1 FROM biofloc.movimientos_inventario m
           WHERE m.producto_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            ''No se pueden cambiar las unidades ni el factor de conversión del producto % porque ya tiene movimientos de inventario'',
            OLD.id
            USING ERRCODE = ''check_violation'';
    END IF;
    RETURN NEW;
END;
';

DROP TRIGGER IF EXISTS trg_proteger_unidades_producto_con_historial
ON biofloc.productos;

CREATE TRIGGER trg_proteger_unidades_producto_con_historial
BEFORE UPDATE OF unidad_id, unidad_comercial_id, factor_conversion
ON biofloc.productos
FOR EACH ROW
EXECUTE FUNCTION biofloc.proteger_unidades_producto_con_historial();

CREATE OR REPLACE VIEW biofloc.vista_disponibilidad_venta_lotes AS
SELECT
    l.id AS lote_id,
    l.codigo AS lote_codigo,
    COALESCE(c.cosechado_kg, 0) AS cosechado_kg,
    COALESCE(v.vendido_kg, 0) AS vendido_kg,
    GREATEST(COALESCE(c.cosechado_kg, 0) - COALESCE(v.vendido_kg, 0), 0) AS disponible_kg
FROM biofloc.lotes l
LEFT JOIN (
    SELECT lote_id, SUM(peso_total_kg) AS cosechado_kg
    FROM biofloc.cosechas
    GROUP BY lote_id
) c ON c.lote_id = l.id
LEFT JOIN (
    SELECT lote_id, SUM(cantidad) AS vendido_kg
    FROM biofloc.detalles_venta
    GROUP BY lote_id
) v ON v.lote_id = l.id;

COMMENT ON VIEW biofloc.vista_disponibilidad_venta_lotes IS
    'Biomasa cosechada, vendida y disponible por lote. Las ventas se expresan en kg.';

COMMIT;
