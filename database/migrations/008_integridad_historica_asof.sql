-- Migración 008: integridad histórica AS-OF.
-- Las validaciones de inventario, población y ventas deben evaluar el estado
-- existente hasta la fecha/hora del evento, no el estado actual.
-- Esta migración reemplaza las funciones de las migraciones 003 y 004 sin
-- modificar los movimientos históricos ya registrados.

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_stock_movimiento()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_afecta_stock SMALLINT;
    v_stock NUMERIC(18,3);
BEGIN
    SELECT afecta_stock
      INTO v_afecta_stock
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF v_afecta_stock IS NULL THEN
        RAISE EXCEPTION 'Tipo de movimiento % no existe', NEW.tipo_movimiento_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad del movimiento debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_afecta_stock = -1 THEN
        PERFORM 1
          FROM biofloc.productos
         WHERE id = NEW.producto_id
         FOR UPDATE;

        SELECT COALESCE(SUM(
            CASE WHEN t.afecta_stock = 1 THEN m.cantidad ELSE -m.cantidad END
        ), 0)
          INTO v_stock
          FROM biofloc.movimientos_inventario m
          JOIN biofloc.tipos_movimiento_inventario t
            ON t.id = m.tipo_movimiento_id
         WHERE m.producto_id = NEW.producto_id
           AND m.fecha_hora <= NEW.fecha_hora;

        IF v_stock < NEW.cantidad THEN
            RAISE EXCEPTION
                'No hay stock suficiente en la fecha del movimiento. Disponible: %, solicitado: %',
                v_stock, NEW.cantidad
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_stock_movimiento
ON biofloc.movimientos_inventario;

CREATE TRIGGER trg_validar_stock_movimiento
BEFORE INSERT ON biofloc.movimientos_inventario
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_stock_movimiento();


CREATE OR REPLACE FUNCTION biofloc.validar_poblacion_mortalidad()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_sembrados INTEGER;
    v_salidas INTEGER;
BEGIN
    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad de mortalidad debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT cantidad_sembrada
      INTO v_sembrados
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR UPDATE;

    IF v_sembrados IS NULL THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT COALESCE(SUM(cantidad), 0)
      INTO v_salidas
      FROM biofloc.mortalidades
     WHERE lote_id = NEW.lote_id
       AND fecha_hora <= NEW.fecha_hora;

    SELECT v_salidas + COALESCE(SUM(cantidad_peces), 0)
      INTO v_salidas
      FROM biofloc.cosechas
     WHERE lote_id = NEW.lote_id
       AND fecha_hora <= NEW.fecha_hora;

    IF v_salidas + NEW.cantidad > v_sembrados THEN
        RAISE EXCEPTION
            'La mortalidad excede la población disponible en la fecha del evento. Disponible: %, solicitado: %',
            GREATEST(v_sembrados - v_salidas, 0), NEW.cantidad
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_poblacion_mortalidad
ON biofloc.mortalidades;

CREATE TRIGGER trg_validar_poblacion_mortalidad
BEFORE INSERT ON biofloc.mortalidades
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_poblacion_mortalidad();


CREATE OR REPLACE FUNCTION biofloc.validar_poblacion_cosecha()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_sembrados INTEGER;
    v_salidas INTEGER;
BEGIN
    IF NEW.cantidad_peces <= 0 THEN
        RAISE EXCEPTION 'La cantidad de peces cosechados debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT cantidad_sembrada
      INTO v_sembrados
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR UPDATE;

    IF v_sembrados IS NULL THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT COALESCE(SUM(cantidad), 0)
      INTO v_salidas
      FROM biofloc.mortalidades
     WHERE lote_id = NEW.lote_id
       AND fecha_hora <= NEW.fecha_hora;

    SELECT v_salidas + COALESCE(SUM(cantidad_peces), 0)
      INTO v_salidas
      FROM biofloc.cosechas
     WHERE lote_id = NEW.lote_id
       AND fecha_hora <= NEW.fecha_hora;

    IF v_salidas + NEW.cantidad_peces > v_sembrados THEN
        RAISE EXCEPTION
            'La cosecha excede la población disponible en la fecha del evento. Disponible: %, solicitado: %',
            GREATEST(v_sembrados - v_salidas, 0), NEW.cantidad_peces
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_poblacion_cosecha
ON biofloc.cosechas;

CREATE TRIGGER trg_validar_poblacion_cosecha
BEFORE INSERT ON biofloc.cosechas
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_poblacion_cosecha();


CREATE OR REPLACE FUNCTION biofloc.validar_disponibilidad_venta()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_cosechado NUMERIC(18,3);
    v_vendido NUMERIC(18,3);
    v_disponible NUMERIC(18,3);
    v_fecha_venta DATE;
    v_limite_cosecha TIMESTAMPTZ;
BEGIN
    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad de venta debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT fecha
      INTO v_fecha_venta
      FROM biofloc.ventas
     WHERE id = NEW.venta_id;

    IF v_fecha_venta IS NULL THEN
        RAISE EXCEPTION 'Venta % no existe', NEW.venta_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    PERFORM 1
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    v_limite_cosecha :=
        ((v_fecha_venta + 1)::timestamp AT TIME ZONE 'America/Bogota');

    SELECT COALESCE(SUM(peso_total_kg), 0)
      INTO v_cosechado
      FROM biofloc.cosechas
     WHERE lote_id = NEW.lote_id
       AND fecha_hora < v_limite_cosecha;

    SELECT COALESCE(SUM(dv.cantidad), 0)
      INTO v_vendido
      FROM biofloc.detalles_venta dv
      JOIN biofloc.ventas v ON v.id = dv.venta_id
     WHERE dv.lote_id = NEW.lote_id
       AND v.fecha <= v_fecha_venta;

    v_disponible := GREATEST(v_cosechado - v_vendido, 0);

    IF NEW.cantidad > v_disponible THEN
        RAISE EXCEPTION
            'Biomasa insuficiente para la venta del lote %. Disponible hasta la fecha de venta: % kg, solicitado: % kg',
            NEW.lote_id, v_disponible, NEW.cantidad
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_disponibilidad_venta
ON biofloc.detalles_venta;

CREATE TRIGGER trg_validar_disponibilidad_venta
BEFORE INSERT ON biofloc.detalles_venta
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_disponibilidad_venta();

COMMIT;
