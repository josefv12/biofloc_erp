-- Migración 010: integridad productiva a nivel de base de datos.
BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_evento_lote()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_siembra DATE;
BEGIN
    SELECT fecha_siembra INTO v_siembra FROM biofloc.lotes WHERE id=NEW.lote_id FOR UPDATE;
    IF v_siembra IS NULL THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id USING ERRCODE='foreign_key_violation';
    END IF;
    IF NEW.fecha_hora < (v_siembra::timestamp AT TIME ZONE 'America/Bogota') THEN
        RAISE EXCEPTION 'La fecha del evento no puede ser anterior a la siembra del lote'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_validar_fecha_biometria ON biofloc.biometrias;
CREATE TRIGGER trg_validar_fecha_biometria BEFORE INSERT OR UPDATE ON biofloc.biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();

DROP TRIGGER IF EXISTS trg_validar_fecha_mortalidad ON biofloc.mortalidades;
CREATE TRIGGER trg_validar_fecha_mortalidad BEFORE INSERT OR UPDATE ON biofloc.mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();

DROP TRIGGER IF EXISTS trg_validar_fecha_cosecha ON biofloc.cosechas;
CREATE TRIGGER trg_validar_fecha_cosecha BEFORE INSERT OR UPDATE ON biofloc.cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();

CREATE OR REPLACE FUNCTION biofloc.validar_muestra_biometria()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_sembrados INTEGER; v_salidas INTEGER;
BEGIN
    SELECT cantidad_sembrada INTO v_sembrados FROM biofloc.lotes WHERE id=NEW.lote_id FOR UPDATE;
    SELECT COALESCE(SUM(m.cantidad),0) INTO v_salidas
      FROM biofloc.mortalidades m WHERE m.lote_id=NEW.lote_id AND m.fecha_hora<=NEW.fecha_hora;
    SELECT v_salidas + COALESCE(SUM(c.cantidad_peces),0) INTO v_salidas
      FROM biofloc.cosechas c WHERE c.lote_id=NEW.lote_id AND c.fecha_hora<=NEW.fecha_hora;
    IF NEW.cantidad_muestra > GREATEST(v_sembrados-v_salidas,0) THEN
        RAISE EXCEPTION 'La muestra biométrica excede la población disponible en la fecha del evento. Disponible: %, solicitado: %',
            GREATEST(v_sembrados-v_salidas,0), NEW.cantidad_muestra USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_validar_muestra_biometria ON biofloc.biometrias;
CREATE TRIGGER trg_validar_muestra_biometria BEFORE INSERT OR UPDATE ON biofloc.biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_muestra_biometria();

COMMIT;
