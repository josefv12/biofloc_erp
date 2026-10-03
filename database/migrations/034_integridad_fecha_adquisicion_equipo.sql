-- 034_integridad_fecha_adquisicion_equipo
SET search_path TO biofloc, public;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_adquisicion_equipo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_fecha_adquisicion_equipo$
DECLARE
    v_min_fecha DATE;
BEGIN
    IF NEW.fecha_adquisicion IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT MIN(fecha) INTO v_min_fecha
    FROM biofloc.mantenimientos
    WHERE equipo_id = NEW.id;

    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a un mantenimiento histórico del equipo'
            USING ERRCODE='check_violation';
    END IF;

    SELECT MIN((fecha_hora AT TIME ZONE 'America/Bogota')::date) INTO v_min_fecha
    FROM biofloc.fallas
    WHERE equipo_id = NEW.id;

    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a una falla histórica del equipo'
            USING ERRCODE='check_violation';
    END IF;

    SELECT MIN((fecha_hora_inicio AT TIME ZONE 'America/Bogota')::date) INTO v_min_fecha
    FROM biofloc.eventos_energia
    WHERE equipo_respaldo_id = NEW.id;

    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a un evento de energía histórico'
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_fecha_adquisicion_equipo$;

DROP TRIGGER IF EXISTS trg_validar_fecha_adquisicion_equipo ON biofloc.equipos;
CREATE TRIGGER trg_validar_fecha_adquisicion_equipo
BEFORE INSERT OR UPDATE OF fecha_adquisicion ON biofloc.equipos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_fecha_adquisicion_equipo();

CREATE OR REPLACE FUNCTION biofloc.validar_evento_no_antes_adquisicion_equipo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_evento_no_antes_adquisicion_equipo$
DECLARE
    v_adquisicion DATE;
BEGIN
    SELECT fecha_adquisicion INTO v_adquisicion
    FROM biofloc.equipos
    WHERE id = NEW.equipo_id;

    IF v_adquisicion IS NOT NULL AND (NEW.fecha_hora AT TIME ZONE 'America/Bogota')::date < v_adquisicion THEN
        RAISE EXCEPTION 'La falla no puede ser anterior a la adquisición del equipo'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_evento_no_antes_adquisicion_equipo$;

DROP TRIGGER IF EXISTS trg_validar_falla_no_antes_adquisicion ON biofloc.fallas;
CREATE TRIGGER trg_validar_falla_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_id, fecha_hora ON biofloc.fallas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_antes_adquisicion_equipo();

CREATE OR REPLACE FUNCTION biofloc.validar_mantenimiento_no_antes_adquisicion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_mantenimiento_no_antes_adquisicion$
DECLARE
    v_adquisicion DATE;
BEGIN
    SELECT fecha_adquisicion INTO v_adquisicion
    FROM biofloc.equipos
    WHERE id = NEW.equipo_id;

    IF v_adquisicion IS NOT NULL AND NEW.fecha < v_adquisicion THEN
        RAISE EXCEPTION 'El mantenimiento no puede ser anterior a la adquisición del equipo'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_mantenimiento_no_antes_adquisicion$;

DROP TRIGGER IF EXISTS trg_validar_mantenimiento_no_antes_adquisicion ON biofloc.mantenimientos;
CREATE TRIGGER trg_validar_mantenimiento_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_id, fecha ON biofloc.mantenimientos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_mantenimiento_no_antes_adquisicion();

CREATE OR REPLACE FUNCTION biofloc.validar_respaldo_no_antes_adquisicion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_respaldo_no_antes_adquisicion$
DECLARE
    v_adquisicion DATE;
BEGIN
    IF NEW.respaldo_activado AND NEW.equipo_respaldo_id IS NOT NULL THEN
        SELECT fecha_adquisicion INTO v_adquisicion
        FROM biofloc.equipos
        WHERE id = NEW.equipo_respaldo_id;

        IF v_adquisicion IS NOT NULL
           AND NEW.fecha_hora_inicio::date < v_adquisicion THEN
            RAISE EXCEPTION 'El evento de energía no puede preceder la adquisición del equipo de respaldo'
                USING ERRCODE='check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_validar_respaldo_no_antes_adquisicion$;

DROP TRIGGER IF EXISTS trg_validar_respaldo_no_antes_adquisicion ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_respaldo_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_respaldo_id, respaldo_activado, fecha_hora_inicio
ON biofloc.eventos_energia
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_respaldo_no_antes_adquisicion();
