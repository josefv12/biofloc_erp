-- 035_transicion_estado_equipo
SET search_path TO biofloc, public;

CREATE OR REPLACE FUNCTION biofloc.validar_transicion_estado_equipo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_transicion_estado_equipo$
DECLARE
    v_actual TEXT;
    v_nuevo TEXT;
BEGIN
    IF NEW.estado_id = OLD.estado_id THEN
        RETURN NEW;
    END IF;

    SELECT nombre INTO v_actual FROM biofloc.estados_equipo WHERE id=OLD.estado_id;
    SELECT nombre INTO v_nuevo FROM biofloc.estados_equipo WHERE id=NEW.estado_id;

    IF v_actual = 'BAJA' THEN
        RAISE EXCEPTION 'Un equipo en estado BAJA no puede volver a otro estado'
            USING ERRCODE='check_violation';
    END IF;

    IF v_nuevo = 'BAJA' THEN
        NEW.activo := FALSE;
    END IF;

    RETURN NEW;
END;
$fn_validar_transicion_estado_equipo$;

DROP TRIGGER IF EXISTS trg_validar_transicion_estado_equipo ON biofloc.equipos;
CREATE TRIGGER trg_validar_transicion_estado_equipo
BEFORE UPDATE OF estado_id ON biofloc.equipos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_transicion_estado_equipo();
