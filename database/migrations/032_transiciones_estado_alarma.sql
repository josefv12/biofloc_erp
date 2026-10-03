-- ============================================================
-- MIGRACIÓN 032: transiciones válidas de estados de alarma
-- ============================================================
-- Flujo semilla: PENDIENTE -> ATENDIDA -> CERRADA.
-- Se permite PENDIENTE -> CERRADA para cierres directos.
-- No se permite reabrir una alarma histórica.
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_transicion_estado_alarma()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_transicion_estado_alarma$
DECLARE
    v_anterior VARCHAR(30);
    v_nuevo VARCHAR(30);
BEGIN
    SELECT nombre INTO v_anterior
    FROM biofloc.estados_alarma
    WHERE id = OLD.estado_alarma_id;

    SELECT nombre INTO v_nuevo
    FROM biofloc.estados_alarma
    WHERE id = NEW.estado_alarma_id;

    IF v_anterior IN ('PENDIENTE', 'ATENDIDA', 'CERRADA')
       AND v_nuevo IN ('PENDIENTE', 'ATENDIDA', 'CERRADA')
       AND NOT (
           (v_anterior = 'PENDIENTE' AND v_nuevo IN ('PENDIENTE', 'ATENDIDA', 'CERRADA'))
           OR (v_anterior = 'ATENDIDA' AND v_nuevo IN ('ATENDIDA', 'CERRADA'))
           OR (v_anterior = 'CERRADA' AND v_nuevo = 'CERRADA')
       )
    THEN
        RAISE EXCEPTION
            'Transición de alarma no permitida: % -> %',
            v_anterior, v_nuevo
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_transicion_estado_alarma$;

DROP TRIGGER IF EXISTS trg_validar_transicion_estado_alarma
    ON biofloc.alarmas;

CREATE TRIGGER trg_validar_transicion_estado_alarma
BEFORE UPDATE OF estado_alarma_id ON biofloc.alarmas
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_transicion_estado_alarma();

COMMIT;
