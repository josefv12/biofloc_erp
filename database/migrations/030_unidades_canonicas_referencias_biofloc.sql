-- ============================================================
-- MIGRACIÓN 030: unidades canónicas de referencias Biofloc
-- ============================================================
-- Las mediciones usan:
--   VOLUMEN_SEDIMENTABLE -> mL/L
--   RELACION_CN          -> C:N
-- Evita comparar valores numéricos expresados en unidades incompatibles.
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION biofloc.validar_unidad_referencia_biofloc()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_unidad_referencia_biofloc$
DECLARE
    v_unidad_esperada VARCHAR(30);
BEGIN
    v_unidad_esperada := CASE NEW.indicador
        WHEN 'VOLUMEN_SEDIMENTABLE' THEN 'mL/L'
        WHEN 'RELACION_CN' THEN 'C:N'
        ELSE NULL
    END;

    IF v_unidad_esperada IS NULL OR NEW.unidad IS DISTINCT FROM v_unidad_esperada THEN
        RAISE EXCEPTION
            'La referencia Biofloc % debe usar la unidad %',
            NEW.indicador, v_unidad_esperada
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_unidad_referencia_biofloc$;

DROP TRIGGER IF EXISTS trg_validar_unidad_referencia_biofloc
    ON biofloc.referencias_biofloc;

CREATE TRIGGER trg_validar_unidad_referencia_biofloc
BEFORE INSERT OR UPDATE OF indicador, unidad ON biofloc.referencias_biofloc
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_unidad_referencia_biofloc();

COMMIT;
