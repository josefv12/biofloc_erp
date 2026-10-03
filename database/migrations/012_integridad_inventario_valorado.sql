-- Migración 012: endurece integridad temporal y valoración del inventario.
-- Se separa de 009 para no modificar una migración histórica ya aplicada.
-- ENTRADA y AJUSTE positivo deben incorporar costo; ningún movimiento puede
-- registrarse con fecha futura.

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_integridad_movimiento_inventario()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_nombre VARCHAR(30);
    v_efecto SMALLINT;
BEGIN
    SELECT nombre, afecta_stock
      INTO v_nombre, v_efecto
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF v_nombre NOT IN ('ENTRADA', 'SALIDA', 'AJUSTE') THEN
        RAISE EXCEPTION 'Tipo de movimiento no permitido: %',
            COALESCE(v_nombre, NEW.tipo_movimiento_id::text)
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' THEN
        IF NEW.efecto_stock IS NULL OR NEW.efecto_stock NOT IN (-1, 1) THEN
            RAISE EXCEPTION 'AJUSTE requiere efecto_stock = 1 o -1'
                USING ERRCODE = 'check_violation';
        END IF;
        v_efecto := NEW.efecto_stock;
    ELSE
        IF NEW.efecto_stock IS NOT NULL THEN
            RAISE EXCEPTION '% no debe informar efecto_stock', v_nombre
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad del movimiento debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del movimiento de inventario no puede estar en el futuro'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' AND NULLIF(BTRIM(NEW.observaciones), '') IS NULL THEN
        RAISE EXCEPTION 'AJUSTE requiere una observación que explique el motivo'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_efecto = 1 AND NEW.costo_unitario IS NULL THEN
        RAISE EXCEPTION '% positivo requiere costo_unitario', v_nombre
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_unitario < 0 THEN
        RAISE EXCEPTION 'El costo unitario no puede ser negativo'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.costo_total IS NOT NULL AND NEW.costo_total < 0 THEN
        RAISE EXCEPTION 'El costo total no puede ser negativo'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_total IS NOT NULL
       AND ABS(NEW.costo_total - NEW.cantidad * NEW.costo_unitario) > 0.01 THEN
        RAISE EXCEPTION 'Costo total inconsistente con cantidad y costo unitario'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_integridad_movimiento_inventario
ON biofloc.movimientos_inventario;

CREATE TRIGGER trg_validar_integridad_movimiento_inventario
BEFORE INSERT OR UPDATE ON biofloc.movimientos_inventario
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_integridad_movimiento_inventario();

COMMIT;
