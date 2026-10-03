-- Migración 015: integridad de la secuencia histórica de población.
-- Al insertar o actualizar una mortalidad/cosecha retroactiva, toda la secuencia
-- posterior del lote debe seguir siendo válida. Evita que un evento anterior
-- vuelva inconsistente una cosecha/mortalidad ya registrada.

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_secuencia_poblacion_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_sembrados INTEGER;
    v_max_salidas BIGINT;
BEGIN
    SELECT cantidad_sembrada
      INTO v_sembrados
      FROM biofloc.lotes
     WHERE id = NEW.lote_id
     FOR UPDATE;

    IF v_sembrados IS NULL THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id
            USING ERRCODE='foreign_key_violation';
    END IF;

    SELECT COALESCE(MAX(salidas_acumuladas), 0)
      INTO v_max_salidas
      FROM (
          SELECT fecha_hora,
                 SUM(cantidad_salida) OVER (
                     ORDER BY fecha_hora
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                 ) AS salidas_acumuladas
          FROM (
              SELECT fecha_hora, cantidad AS cantidad_salida
                FROM biofloc.mortalidades
               WHERE lote_id = NEW.lote_id

              UNION ALL

              SELECT fecha_hora, cantidad_peces AS cantidad_salida
                FROM biofloc.cosechas
               WHERE lote_id = NEW.lote_id
          ) eventos
      ) secuencia;

    IF v_max_salidas > v_sembrados THEN
        RAISE EXCEPTION
            'La secuencia histórica del lote % deja la población negativa. Máximo de salidas acumuladas: %, sembrados: %',
            NEW.lote_id, v_max_salidas, v_sembrados
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_secuencia_poblacion_mortalidad
ON biofloc.mortalidades;

CREATE CONSTRAINT TRIGGER trg_validar_secuencia_poblacion_mortalidad
AFTER INSERT OR UPDATE ON biofloc.mortalidades
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_secuencia_poblacion_historica();

DROP TRIGGER IF EXISTS trg_validar_secuencia_poblacion_cosecha
ON biofloc.cosechas;

CREATE CONSTRAINT TRIGGER trg_validar_secuencia_poblacion_cosecha
AFTER INSERT OR UPDATE ON biofloc.cosechas
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_secuencia_poblacion_historica();

COMMIT;
