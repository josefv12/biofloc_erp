-- 033_integrIDAD_EQUIPOS_RESPALDO
-- Catálogos activos y equipos de respaldo realmente operativos.
SET search_path TO biofloc, public;

CREATE OR REPLACE FUNCTION biofloc.validar_catalogos_equipo_activos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_catalogos_equipo_activos$
DECLARE
    v_tipo_activo BOOLEAN;
    v_estado_activo BOOLEAN;
BEGIN
    SELECT activo INTO v_tipo_activo FROM tipos_equipo WHERE id = NEW.tipo_equipo_id;
    IF v_tipo_activo IS NULL THEN
        RAISE EXCEPTION 'El tipo de equipo % no existe', NEW.tipo_equipo_id
            USING ERRCODE='foreign_key_violation';
    END IF;
    IF NOT v_tipo_activo THEN
        RAISE EXCEPTION 'El tipo de equipo % está inactivo', NEW.tipo_equipo_id
            USING ERRCODE='check_violation';
    END IF;

    SELECT activo INTO v_estado_activo FROM estados_equipo WHERE id = NEW.estado_id;
    IF v_estado_activo IS NULL THEN
        RAISE EXCEPTION 'El estado de equipo % no existe', NEW.estado_id
            USING ERRCODE='foreign_key_violation';
    END IF;
    IF NOT v_estado_activo THEN
        RAISE EXCEPTION 'El estado de equipo % está inactivo', NEW.estado_id
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_catalogos_equipo_activos$;

DROP TRIGGER IF EXISTS trg_validar_catalogos_equipo_activos ON biofloc.equipos;
CREATE TRIGGER trg_validar_catalogos_equipo_activos
BEFORE INSERT OR UPDATE OF tipo_equipo_id, estado_id
ON biofloc.equipos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_catalogos_equipo_activos();

CREATE OR REPLACE FUNCTION biofloc.validar_equipo_respaldo_operativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_equipo_respaldo_operativo$
DECLARE
    v_activo BOOLEAN;
    v_estado TEXT;
    v_estado_activo BOOLEAN;
BEGIN
    IF NEW.respaldo_activado AND NEW.equipo_respaldo_id IS NULL THEN
        RAISE EXCEPTION 'equipo_respaldo_id es obligatorio cuando respaldo_activado=true'
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.respaldo_activado THEN
        SELECT e.activo, ee.nombre, ee.activo
        INTO v_activo, v_estado, v_estado_activo
        FROM biofloc.equipos e
        JOIN biofloc.estados_equipo ee ON ee.id = e.estado_id
        WHERE e.id = NEW.equipo_respaldo_id;

        IF v_activo IS NULL THEN
            RAISE EXCEPTION 'El equipo de respaldo % no existe', NEW.equipo_respaldo_id
                USING ERRCODE='foreign_key_violation';
        END IF;
        IF NOT v_activo OR NOT v_estado_activo OR v_estado <> 'OPERATIVO' THEN
            RAISE EXCEPTION 'El equipo de respaldo debe estar activo y en estado OPERATIVO'
                USING ERRCODE='check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$fn_validar_equipo_respaldo_operativo$;

DROP TRIGGER IF EXISTS trg_validar_equipo_respaldo_operativo ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_equipo_respaldo_operativo
BEFORE INSERT OR UPDATE OF respaldo_activado, equipo_respaldo_id
ON biofloc.eventos_energia
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_equipo_respaldo_operativo();
