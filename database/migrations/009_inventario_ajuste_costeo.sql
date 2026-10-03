-- Migración 009: inventario con AJUSTE direccional y costeo histórico.
-- ENTRADA y SALIDA tienen efecto fijo. AJUSTE usa efecto_stock en la fila.
-- Las salidas/ajustes negativos congelan el costo promedio del stock AS-OF.

BEGIN;

ALTER TABLE biofloc.movimientos_inventario
    ADD COLUMN IF NOT EXISTS efecto_stock SMALLINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'movimientos_inventario_efecto_stock_check'
          AND conrelid = 'biofloc.movimientos_inventario'::regclass
    ) THEN
        ALTER TABLE biofloc.movimientos_inventario
            ADD CONSTRAINT movimientos_inventario_efecto_stock_check
            CHECK (efecto_stock IS NULL OR efecto_stock IN (-1, 1));
    END IF;
END $$;

-- El catálogo queda definido por tres tipos. AJUSTE mantiene +1 como efecto
-- base para compatibilidad del catálogo; el sentido real vive en el movimiento.
INSERT INTO biofloc.tipos_movimiento_inventario (nombre, descripcion, afecta_stock)
SELECT 'AJUSTE', 'Ajuste manual de inventario con efecto positivo o negativo', 1
WHERE NOT EXISTS (
    SELECT 1 FROM biofloc.tipos_movimiento_inventario WHERE nombre = 'AJUSTE'
);

CREATE OR REPLACE FUNCTION biofloc.efecto_movimiento_inventario(
    p_tipo_id BIGINT,
    p_efecto_stock SMALLINT
)
RETURNS SMALLINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_nombre VARCHAR(30);
    v_efecto SMALLINT;
BEGIN
    SELECT nombre, afecta_stock
      INTO v_nombre, v_efecto
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = p_tipo_id;

    IF v_nombre IS NULL THEN
        RAISE EXCEPTION 'Tipo de movimiento % no existe', p_tipo_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF v_nombre = 'AJUSTE' THEN
        IF p_efecto_stock IS NULL OR p_efecto_stock NOT IN (-1, 1) THEN
            RAISE EXCEPTION 'AJUSTE requiere efecto_stock = 1 o -1'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN p_efecto_stock;
    END IF;

    IF p_efecto_stock IS NOT NULL THEN
        RAISE EXCEPTION '% no debe informar efecto_stock', v_nombre
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_nombre = 'ENTRADA' THEN
        RETURN 1;
    ELSIF v_nombre = 'SALIDA' THEN
        RETURN -1;
    END IF;

    RAISE EXCEPTION 'Tipo de movimiento no permitido: %. Use ENTRADA, SALIDA o AJUSTE', v_nombre
        USING ERRCODE = 'check_violation';
END;
$$;

CREATE OR REPLACE FUNCTION biofloc.validar_stock_movimiento()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_efecto SMALLINT;
    v_stock NUMERIC(18,3);
    v_nombre VARCHAR(30);
BEGIN
    SELECT nombre
      INTO v_nombre
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    v_efecto := biofloc.efecto_movimiento_inventario(
        NEW.tipo_movimiento_id, NEW.efecto_stock
    );

    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad del movimiento debe ser mayor que cero'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' AND NULLIF(BTRIM(NEW.observaciones), '') IS NULL THEN
        RAISE EXCEPTION 'AJUSTE requiere una observación que explique el motivo'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' AND v_efecto = 1 AND NEW.costo_unitario IS NULL THEN
        RAISE EXCEPTION 'AJUSTE positivo requiere costo_unitario'
            USING ERRCODE = 'check_violation';
    END IF;

    IF v_efecto = -1 THEN
        PERFORM 1
          FROM biofloc.productos
         WHERE id = NEW.producto_id
         FOR UPDATE;

        SELECT COALESCE(SUM(
            CASE
                WHEN t.nombre = 'AJUSTE' THEN m.cantidad * m.efecto_stock
                ELSE m.cantidad * t.afecta_stock
            END
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

CREATE OR REPLACE VIEW biofloc.vista_stock_productos AS
SELECT
    p.id AS producto_id,
    p.codigo,
    p.nombre,
    u.simbolo AS unidad,
    COALESCE(
        SUM(
            CASE
                WHEN tmi.nombre = 'AJUSTE' THEN mi.cantidad * mi.efecto_stock
                ELSE mi.cantidad * tmi.afecta_stock
            END
        ),
        0
    ) AS stock_actual,
    p.stock_minimo
FROM biofloc.productos p
JOIN biofloc.unidades u
  ON u.id = p.unidad_id
LEFT JOIN biofloc.movimientos_inventario mi
  ON mi.producto_id = p.id
LEFT JOIN biofloc.tipos_movimiento_inventario tmi
  ON tmi.id = mi.tipo_movimiento_id
GROUP BY
    p.id,
    p.codigo,
    p.nombre,
    u.simbolo,
    p.stock_minimo;

-- Reglas adicionales de integridad: solo los tres tipos permitidos y coherencia
-- entre costo total y costo unitario/cantidad cuando el costo se informa.
CREATE OR REPLACE FUNCTION biofloc.validar_integridad_movimiento_inventario()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $
DECLARE
    v_nombre VARCHAR(30);
BEGIN
    SELECT nombre INTO v_nombre
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF v_nombre NOT IN ('ENTRADA', 'SALIDA', 'AJUSTE') THEN
        RAISE EXCEPTION 'Tipo de movimiento no permitido: %', COALESCE(v_nombre, NEW.tipo_movimiento_id::text)
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_unitario < 0 THEN
        RAISE EXCEPTION 'El costo unitario no puede ser negativo' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.costo_total IS NOT NULL AND NEW.costo_total < 0 THEN
        RAISE EXCEPTION 'El costo total no puede ser negativo' USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_total IS NOT NULL
       AND ABS(NEW.costo_total - (NEW.cantidad * NEW.costo_unitario)) > 0.01 THEN
        RAISE EXCEPTION 'Costo total inconsistente con cantidad y costo unitario' USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$;

DROP TRIGGER IF EXISTS trg_validar_integridad_movimiento_inventario
ON biofloc.movimientos_inventario;
CREATE TRIGGER trg_validar_integridad_movimiento_inventario
BEFORE INSERT OR UPDATE ON biofloc.movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_integridad_movimiento_inventario();

COMMIT;
