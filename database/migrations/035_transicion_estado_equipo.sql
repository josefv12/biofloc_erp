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
    IF TG_OP = 'UPDATE' AND NEW.estado_id = OLD.estado_id THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        SELECT nombre INTO v_actual FROM biofloc.estados_equipo WHERE id=OLD.estado_id;
    END IF;
    SELECT nombre INTO v_nuevo FROM biofloc.estados_equipo WHERE id=NEW.estado_id;

    IF TG_OP = 'UPDATE' AND v_actual = 'BAJA' THEN
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
BEFORE INSERT OR UPDATE OF estado_id ON biofloc.equipos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_transicion_estado_equipo();

    
-- Consistencia de duración de eventos de energía.
CREATE OR REPLACE FUNCTION biofloc.validar_duracion_evento_energia()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_duracion_evento_energia$
DECLARE v_duracion INTEGER;
BEGIN
    IF NEW.fecha_hora_fin IS NULL THEN
        IF NEW.duracion_minutos IS NOT NULL THEN
            RAISE EXCEPTION 'Un evento de energía abierto no puede tener duración' USING ERRCODE='check_violation';
        END IF;
        RETURN NEW;
    END IF;
    v_duracion := FLOOR(EXTRACT(EPOCH FROM (NEW.fecha_hora_fin - NEW.fecha_hora_inicio))/60)::INTEGER;
    IF v_duracion < 0 OR NEW.duracion_minutos IS DISTINCT FROM v_duracion THEN
        RAISE EXCEPTION 'La duración del evento de energía no coincide con su intervalo' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_duracion_evento_energia$;

DROP TRIGGER IF EXISTS trg_validar_duracion_evento_energia ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_duracion_evento_energia
BEFORE INSERT OR UPDATE OF fecha_hora_inicio, fecha_hora_fin, duracion_minutos
ON biofloc.eventos_energia
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_duracion_evento_energia();

CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_falla_historica()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_impedir_modificacion_falla_historica$
BEGIN
    RAISE EXCEPTION 'La falla histórica % es inmutable', OLD.id USING ERRCODE='check_violation';
END;
$fn_impedir_modificacion_falla_historica$;

DROP TRIGGER IF EXISTS trg_inmutabilidad_fallas ON biofloc.fallas;
CREATE TRIGGER trg_inmutabilidad_fallas
BEFORE UPDATE OR DELETE ON biofloc.fallas
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_falla_historica();
