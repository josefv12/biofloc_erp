-- Migración 019: consistencia temporal con fecha_cierre de lotes.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_evento_no_despues_cierre()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_evento_no_despues_cierre$
DECLARE
    v_fecha_cierre DATE;
BEGIN
    SELECT fecha_cierre INTO v_fecha_cierre
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR SHARE;

    IF v_fecha_cierre IS NOT NULL AND NEW.fecha_hora::date > v_fecha_cierre THEN
        RAISE EXCEPTION 'El evento del lote % no puede ser posterior a su fecha de cierre', NEW.lote_id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_evento_no_despues_cierre$;

CREATE OR REPLACE FUNCTION biofloc.validar_cierre_no_anterior_eventos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_cierre_no_anterior_eventos$
DECLARE
    v_ultimo TIMESTAMPTZ;
BEGIN
    IF NEW.fecha_cierre IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT MAX(fecha_evento) INTO v_ultimo
      FROM (
          SELECT fecha_hora AS fecha_evento FROM biofloc.biometrias WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.mortalidades WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.cosechas WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.alimentaciones WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.mediciones_biofloc WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.mediciones_agua WHERE lote_id = NEW.id
          UNION ALL SELECT fecha_hora FROM biofloc.aplicaciones_biofloc WHERE lote_id = NEW.id
      ) eventos;

    IF v_ultimo IS NOT NULL AND v_ultimo::date > NEW.fecha_cierre THEN
        RAISE EXCEPTION 'La fecha de cierre no puede ser anterior al último evento histórico del lote %', NEW.id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_cierre_no_anterior_eventos$;

DROP TRIGGER IF EXISTS trg_validar_cierre_no_anterior_eventos ON biofloc.lotes;
CREATE TRIGGER trg_validar_cierre_no_anterior_eventos
BEFORE UPDATE OF fecha_cierre ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_cierre_no_anterior_eventos();

DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_biometrias ON biofloc.biometrias;
CREATE TRIGGER trg_evento_no_despues_cierre_biometrias BEFORE INSERT OR UPDATE ON biofloc.biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_mortalidades ON biofloc.mortalidades;
CREATE TRIGGER trg_evento_no_despues_cierre_mortalidades BEFORE INSERT OR UPDATE ON biofloc.mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_cosechas ON biofloc.cosechas;
CREATE TRIGGER trg_evento_no_despues_cierre_cosechas BEFORE INSERT OR UPDATE ON biofloc.cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_alimentaciones ON biofloc.alimentaciones;
CREATE TRIGGER trg_evento_no_despues_cierre_alimentaciones BEFORE INSERT OR UPDATE ON biofloc.alimentaciones
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_biofloc ON biofloc.mediciones_biofloc;
CREATE TRIGGER trg_evento_no_despues_cierre_biofloc BEFORE INSERT OR UPDATE ON biofloc.mediciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_agua ON biofloc.mediciones_agua;
CREATE TRIGGER trg_evento_no_despues_cierre_agua BEFORE INSERT OR UPDATE ON biofloc.mediciones_agua
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_aplicaciones ON biofloc.aplicaciones_biofloc;
CREATE TRIGGER trg_evento_no_despues_cierre_aplicaciones BEFORE INSERT OR UPDATE ON biofloc.aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();

COMMIT;
