-- Migración 016: integridad temporal de eventos operativos auxiliares.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_falla_no_futura()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_falla_futura$
BEGIN
    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora de la falla no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_falla_futura$;

DROP TRIGGER IF EXISTS trg_validar_fecha_falla_futura ON biofloc.fallas;
CREATE TRIGGER trg_validar_fecha_falla_futura BEFORE INSERT OR UPDATE ON biofloc.fallas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_falla_no_futura();

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_mantenimiento_no_futura()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_mantenimiento_futuro$
BEGIN
    IF NEW.fecha > CURRENT_DATE THEN
        RAISE EXCEPTION 'La fecha del mantenimiento no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_mantenimiento_futuro$;

DROP TRIGGER IF EXISTS trg_validar_fecha_mantenimiento_futura ON biofloc.mantenimientos;
CREATE TRIGGER trg_validar_fecha_mantenimiento_futura BEFORE INSERT OR UPDATE ON biofloc.mantenimientos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_mantenimiento_no_futura();

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_evento_energia_no_futura()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_energia_futura$
BEGIN
    IF NEW.fecha_hora_inicio > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora de inicio del evento de energía no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    IF NEW.fecha_hora_fin IS NOT NULL AND NEW.fecha_hora_fin > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora de fin del evento de energía no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_energia_futura$;

DROP TRIGGER IF EXISTS trg_validar_fecha_evento_energia_futura ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_fecha_evento_energia_futura BEFORE INSERT OR UPDATE ON biofloc.eventos_energia
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_energia_no_futura();

COMMIT;
