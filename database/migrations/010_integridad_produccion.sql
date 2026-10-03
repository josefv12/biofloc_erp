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

    
-- Consistencia matemática de la cosecha: el promedio declarado debe corresponder
-- al peso total y número de peces, con tolerancia de 0.001 g.
CREATE OR REPLACE FUNCTION biofloc.validar_promedio_cosecha()
RETURNS TRIGGER LANGUAGE plpgsql AS $
DECLARE v_esperado NUMERIC;
BEGIN
    v_esperado := (NEW.peso_total_kg * 1000) / NULLIF(NEW.cantidad_peces, 0);
    IF NEW.peso_promedio_g IS NOT NULL
       AND ABS(NEW.peso_promedio_g - v_esperado) > 0.001 THEN
        RAISE EXCEPTION 'El peso promedio de la cosecha no coincide con peso total/cantidad. Esperado: %, recibido: %',
            ROUND(v_esperado, 3), NEW.peso_promedio_g USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $;

DROP TRIGGER IF EXISTS trg_validar_promedio_cosecha ON biofloc.cosechas;
CREATE TRIGGER trg_validar_promedio_cosecha
BEFORE INSERT OR UPDATE ON biofloc.cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_promedio_cosecha();

-- Ningún evento operativo puede quedar fechado en el futuro.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_evento_no_futura()
RETURNS TRIGGER LANGUAGE plpgsql AS $
BEGIN
    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del evento no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $;

DROP TRIGGER IF EXISTS trg_validar_fecha_biometria_futura ON biofloc.biometrias;
CREATE TRIGGER trg_validar_fecha_biometria_futura BEFORE INSERT OR UPDATE ON biofloc.biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_mortalidad_futura ON biofloc.mortalidades;
CREATE TRIGGER trg_validar_fecha_mortalidad_futura BEFORE INSERT OR UPDATE ON biofloc.mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_cosecha_futura ON biofloc.cosechas;
CREATE TRIGGER trg_validar_fecha_cosecha_futura BEFORE INSERT OR UPDATE ON biofloc.cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_alimentacion_futura ON biofloc.alimentaciones;
CREATE TRIGGER trg_validar_fecha_alimentacion_futura BEFORE INSERT OR UPDATE ON biofloc.alimentaciones
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_medicion_biofloc_futura ON biofloc.mediciones_biofloc;
CREATE TRIGGER trg_validar_fecha_medicion_biofloc_futura BEFORE INSERT OR UPDATE ON biofloc.mediciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_medicion_agua_futura ON biofloc.mediciones_agua;
CREATE TRIGGER trg_validar_fecha_medicion_agua_futura BEFORE INSERT OR UPDATE ON biofloc.mediciones_agua
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

DROP TRIGGER IF EXISTS trg_validar_fecha_aplicacion_biofloc_futura ON biofloc.aplicaciones_biofloc;
CREATE TRIGGER trg_validar_fecha_aplicacion_biofloc_futura BEFORE INSERT OR UPDATE ON biofloc.aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();

COMMIT;
