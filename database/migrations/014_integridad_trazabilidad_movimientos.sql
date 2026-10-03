-- Migración 014: integridad de trazabilidad entre eventos productivos y salidas de inventario.
-- Una salida referenciada como ALIMENTACION o APLICACION_BIOFLOC debe coincidir
-- exactamente con el evento origen: producto, cantidad, fecha/hora y tipo SALIDA.

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_trazabilidad_movimiento_automatico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_tipo VARCHAR(30);
    v_producto BIGINT;
    v_cantidad NUMERIC;
    v_fecha TIMESTAMPTZ;
BEGIN
    IF NEW.referencia_tipo IS NULL OR NEW.referencia_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT nombre INTO v_tipo
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF NEW.referencia_tipo = 'DETALLE_COMPRA' THEN
        IF v_tipo <> 'ENTRADA' THEN
            RAISE EXCEPTION 'Un detalle de compra solo puede generar un movimiento ENTRADA'
                USING ERRCODE='check_violation';
        END IF;

        SELECT producto_id, cantidad
          INTO v_producto, v_cantidad
          FROM biofloc.detalles_compra
         WHERE id = NEW.referencia_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Detalle de compra % no existe para la trazabilidad',
                NEW.referencia_id USING ERRCODE='foreign_key_violation';
        END IF;

    ELSIF NEW.referencia_tipo = 'ALIMENTACION' THEN
        IF v_tipo <> 'SALIDA' THEN
            RAISE EXCEPTION 'Una alimentación solo puede generar un movimiento SALIDA'
                USING ERRCODE='check_violation';
        END IF;

        SELECT producto_id, cantidad, fecha_hora
          INTO v_producto, v_cantidad, v_fecha
          FROM biofloc.alimentaciones
         WHERE id = NEW.referencia_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Alimentación % no existe para la trazabilidad'
                , NEW.referencia_id USING ERRCODE='foreign_key_violation';
        END IF;

    ELSIF NEW.referencia_tipo = 'APLICACION_BIOFLOC' THEN
        IF v_tipo <> 'SALIDA' THEN
            RAISE EXCEPTION 'Una aplicación Biofloc solo puede generar un movimiento SALIDA'
                USING ERRCODE='check_violation';
        END IF;

        SELECT producto_id, cantidad, fecha_hora
          INTO v_producto, v_cantidad, v_fecha
          FROM biofloc.aplicaciones_biofloc
         WHERE id = NEW.referencia_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Aplicación Biofloc % no existe para la trazabilidad'
                , NEW.referencia_id USING ERRCODE='foreign_key_violation';
        END IF;

        IF v_producto IS NULL OR v_cantidad IS NULL OR v_cantidad <= 0 THEN
            RAISE EXCEPTION 'La aplicación Biofloc no tiene un consumo de inventario válido'
                USING ERRCODE='check_violation';
        END IF;
    ELSE
        RAISE EXCEPTION 'Referencia de inventario no permitida: %', NEW.referencia_tipo
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.producto_id <> v_producto THEN
        RAISE EXCEPTION 'El producto del movimiento no coincide con el evento origen'
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.cantidad <> v_cantidad THEN
        RAISE EXCEPTION 'La cantidad del movimiento no coincide con el evento origen'
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.fecha_hora <> v_fecha THEN
        RAISE EXCEPTION 'La fecha/hora del movimiento no coincide con el evento origen'
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_trazabilidad_movimiento_automatico
ON biofloc.movimientos_inventario;

CREATE TRIGGER trg_validar_trazabilidad_movimiento_automatico
BEFORE INSERT OR UPDATE ON biofloc.movimientos_inventario
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_trazabilidad_movimiento_automatico();

COMMIT;
