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

    
-- Integridad histórica del catálogo de tipos de mantenimiento.
-- El nombre de un tipo ya referenciado no puede cambiar: los mantenimientos
-- históricos solo almacenan tipo_mantenimiento_id y los reportes resuelven el
-- nombre desde este catálogo.
CREATE OR REPLACE FUNCTION biofloc.validar_tipo_mantenimiento_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_tipo_mantenimiento_historico$
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (
           SELECT 1
           FROM biofloc.mantenimientos
           WHERE tipo_mantenimiento_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'El tipo de mantenimiento % ya tiene registros históricos y no puede renombrarse',
            OLD.id
            USING ERRCODE='check_violation';
    END IF;

    IF TG_OP = 'INSERT' OR NEW.tipo_mantenimiento_id IS DISTINCT FROM OLD.tipo_mantenimiento_id THEN
        IF NOT EXISTS (
            SELECT 1
            FROM biofloc.tipos_mantenimiento
            WHERE id = NEW.tipo_mantenimiento_id
              AND activo = TRUE
        ) THEN
            RAISE EXCEPTION
                'El tipo de mantenimiento % debe existir y estar activo',
                NEW.tipo_mantenimiento_id
                USING ERRCODE='check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$fn_validar_tipo_mantenimiento_historico$;

DROP TRIGGER IF EXISTS trg_validar_tipo_mantenimiento_historico ON biofloc.tipos_mantenimiento;
CREATE TRIGGER trg_validar_tipo_mantenimiento_historico
BEFORE UPDATE OF nombre ON biofloc.tipos_mantenimiento
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_tipo_mantenimiento_historico();

DROP TRIGGER IF EXISTS trg_validar_tipo_mantenimiento_activo ON biofloc.mantenimientos;
CREATE TRIGGER trg_validar_tipo_mantenimiento_activo
BEFORE INSERT OR UPDATE OF tipo_mantenimiento_id ON biofloc.mantenimientos
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_tipo_mantenimiento_historico();

    
-- Los nombres de catálogos de equipos son parte de la semántica de las
-- referencias históricas y de reglas operativas (OPERATIVO/BAJA).
CREATE OR REPLACE FUNCTION biofloc.validar_catalogo_equipo_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_catalogo_equipo_historico$
BEGIN
    IF TG_TABLE_NAME = 'tipos_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (
           SELECT 1 FROM biofloc.equipos WHERE tipo_equipo_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'El tipo de equipo % ya está referenciado y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'estados_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (
           SELECT 1 FROM biofloc.equipos WHERE estado_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'El estado de equipo % ya está referenciado y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'estados_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND OLD.nombre IN ('OPERATIVO', 'BAJA', 'FUERA_DE_SERVICIO')
    THEN
        RAISE EXCEPTION
            'El estado de equipo % es un nombre reservado por las reglas operativas y no puede renombrarse',
            OLD.nombre USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_catalogo_equipo_historico$;

DROP TRIGGER IF EXISTS trg_validar_tipo_equipo_historico ON biofloc.tipos_equipo;
CREATE TRIGGER trg_validar_tipo_equipo_historico
BEFORE UPDATE OF nombre ON biofloc.tipos_equipo
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogo_equipo_historico();

DROP TRIGGER IF EXISTS trg_validar_estado_equipo_historico ON biofloc.estados_equipo;
CREATE TRIGGER trg_validar_estado_equipo_historico
BEFORE UPDATE OF nombre ON biofloc.estados_equipo
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogo_equipo_historico();

    
-- Integridad histórica y de catálogo para agua/Biofloc.
CREATE OR REPLACE FUNCTION biofloc.validar_catalogos_agua_biofloc()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_catalogos_agua_biofloc$
BEGIN
    IF TG_TABLE_NAME = 'parametros_agua'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND (
           EXISTS (SELECT 1 FROM biofloc.mediciones_agua WHERE parametro_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_agua WHERE parametro_id = OLD.id)
       )
    THEN
        RAISE EXCEPTION
            'El parámetro de agua % ya tiene historial/referencias y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'referencias_agua'
       AND (
           TG_OP = 'INSERT'
           OR NEW.parametro_id IS DISTINCT FROM OLD.parametro_id
       )
       AND NOT EXISTS (
           SELECT 1 FROM biofloc.parametros_agua
           WHERE id = NEW.parametro_id AND activo = TRUE
       )
    THEN
        RAISE EXCEPTION
            'El parámetro de agua % debe existir y estar activo',
            NEW.parametro_id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'aplicaciones_biofloc'
       AND (
           TG_OP = 'INSERT'
           OR NEW.tipo_aplicacion_id IS DISTINCT FROM OLD.tipo_aplicacion_id
       )
       AND NOT EXISTS (
           SELECT 1 FROM biofloc.tipos_aplicacion_biofloc
           WHERE id = NEW.tipo_aplicacion_id AND activo = TRUE
       )
    THEN
        RAISE EXCEPTION
            'El tipo de aplicación Biofloc % debe existir y estar activo',
            NEW.tipo_aplicacion_id USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_catalogos_agua_biofloc$;

DROP TRIGGER IF EXISTS trg_validar_nombre_parametro_agua_historico ON biofloc.parametros_agua;
CREATE TRIGGER trg_validar_nombre_parametro_agua_historico
BEFORE UPDATE OF nombre ON biofloc.parametros_agua
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_agua_biofloc();

DROP TRIGGER IF EXISTS trg_validar_parametro_agua_referencia_activo ON biofloc.referencias_agua;
CREATE TRIGGER trg_validar_parametro_agua_referencia_activo
BEFORE INSERT OR UPDATE OF parametro_id ON biofloc.referencias_agua
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_agua_biofloc();

DROP TRIGGER IF EXISTS trg_validar_tipo_aplicacion_biofloc_activo ON biofloc.aplicaciones_biofloc;
CREATE TRIGGER trg_validar_tipo_aplicacion_biofloc_activo
BEFORE INSERT OR UPDATE OF tipo_aplicacion_id ON biofloc.aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_agua_biofloc();

    
-- Catálogos de especie y etapa: sus nombres son parte de la interpretación
-- histórica de lotes y referencias.
CREATE OR REPLACE FUNCTION biofloc.validar_catalogos_produccion_historicos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_catalogos_produccion_historicos$
BEGIN
    IF TG_TABLE_NAME = 'especies'
       AND NEW.nombre_comun IS DISTINCT FROM OLD.nombre_comun
       AND (
           EXISTS (SELECT 1 FROM biofloc.lotes WHERE especie_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_produccion WHERE especie_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_agua WHERE especie_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_biofloc WHERE especie_id = OLD.id)
       )
    THEN
        RAISE EXCEPTION 'La especie % ya tiene historial o referencias y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'etapas_productivas'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND (
           EXISTS (SELECT 1 FROM biofloc.lotes WHERE etapa_productiva_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_produccion WHERE etapa_productiva_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_agua WHERE etapa_productiva_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.referencias_biofloc WHERE etapa_productiva_id = OLD.id)
       )
    THEN
        RAISE EXCEPTION 'La etapa productiva % ya tiene historial o referencias y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'referencias_produccion'
       AND (
           TG_OP = 'INSERT'
           OR NEW.especie_id IS DISTINCT FROM OLD.especie_id
           OR NEW.etapa_productiva_id IS DISTINCT FROM OLD.etapa_productiva_id
       )
       AND (
           NOT EXISTS (SELECT 1 FROM biofloc.especies WHERE id = NEW.especie_id AND activo = TRUE)
           OR NOT EXISTS (SELECT 1 FROM biofloc.etapas_productivas WHERE id = NEW.etapa_productiva_id AND activo = TRUE)
       )
    THEN
        RAISE EXCEPTION 'La especie y la etapa de una referencia de producción deben existir y estar activas'
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_catalogos_produccion_historicos$;

DROP TRIGGER IF EXISTS trg_validar_nombre_especie_historico ON biofloc.especies;
CREATE TRIGGER trg_validar_nombre_especie_historico
BEFORE UPDATE OF nombre_comun ON biofloc.especies
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_produccion_historicos();

DROP TRIGGER IF EXISTS trg_validar_nombre_etapa_historico ON biofloc.etapas_productivas;
CREATE TRIGGER trg_validar_nombre_etapa_historico
BEFORE UPDATE OF nombre ON biofloc.etapas_productivas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_produccion_historicos();

DROP TRIGGER IF EXISTS trg_validar_referencia_produccion_catalogos_activos ON biofloc.referencias_produccion;
CREATE TRIGGER trg_validar_referencia_produccion_catalogos_activos
BEFORE INSERT OR UPDATE OF especie_id, etapa_productiva_id
ON biofloc.referencias_produccion
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_produccion_historicos();

    
-- Integridad semántica de estados de lote/estanque.
CREATE OR REPLACE FUNCTION biofloc.validar_estado_lote_operativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_estado_lote_operativo$
DECLARE
    nombre_nuevo TEXT;
    nombre_anterior TEXT;
    activo_catalogo BOOLEAN;
BEGIN
    SELECT nombre, activo INTO nombre_nuevo, activo_catalogo FROM biofloc.estados_lote WHERE id = NEW.estado_id;
    IF NOT FOUND OR NOT activo_catalogo THEN
        RAISE EXCEPTION 'El estado de lote debe existir y estar activo' USING ERRCODE='check_violation';
    END IF;

    SELECT nombre INTO nombre_anterior FROM biofloc.estados_lote WHERE id = OLD.estado_id;

    IF nombre_anterior IN ('FINALIZADO', 'CANCELADO') AND nombre_nuevo <> nombre_anterior THEN
        RAISE EXCEPTION 'Un lote % no puede reabrirse ni cambiar de estado', nombre_anterior USING ERRCODE='check_violation';
    END IF;

    IF nombre_nuevo IN ('FINALIZADO', 'CANCELADO') AND NEW.fecha_cierre IS NULL THEN
        RAISE EXCEPTION 'El estado % requiere fecha_cierre', nombre_nuevo USING ERRCODE='check_violation';
    END IF;

    IF nombre_nuevo = 'ACTIVO' AND NEW.fecha_cierre IS NOT NULL THEN
        RAISE EXCEPTION 'Un lote ACTIVO no puede tener fecha_cierre' USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_estado_lote_operativo$;

DROP TRIGGER IF EXISTS trg_validar_estado_lote_operativo ON biofloc.lotes;
CREATE TRIGGER trg_validar_estado_lote_operativo
BEFORE INSERT OR UPDATE OF estado_id, fecha_cierre ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_estado_lote_operativo();

CREATE OR REPLACE FUNCTION biofloc.validar_estado_estanque_operativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_estado_estanque_operativo$
DECLARE
    nombre_nuevo TEXT;
    activo_catalogo BOOLEAN;
BEGIN
    PERFORM pg_advisory_xact_lock(2147483000, NEW.id);

    SELECT nombre, activo INTO nombre_nuevo, activo_catalogo
    FROM biofloc.estados_estanque WHERE id = NEW.estado_id;

    IF NOT FOUND OR NOT activo_catalogo THEN
        RAISE EXCEPTION 'El estado de estanque debe existir y estar activo' USING ERRCODE='check_violation';
    END IF;

    IF NEW.activo = FALSE
       AND EXISTS (
           SELECT 1
           FROM biofloc.lotes l
           JOIN biofloc.estados_lote el ON el.id = l.estado_id
           WHERE l.estanque_id = NEW.id AND el.nombre = 'ACTIVO'
       )
    THEN
        RAISE EXCEPTION 'No se puede desactivar un estanque con un lote ACTIVO' USING ERRCODE='check_violation';
    END IF;

    IF EXISTS (
           SELECT 1 FROM biofloc.lotes l
           JOIN biofloc.estados_lote el ON el.id = l.estado_id
           WHERE l.estanque_id = NEW.id AND el.nombre = 'ACTIVO'
       )
       AND nombre_nuevo <> 'OCUPADO'
    THEN
        RAISE EXCEPTION 'Un estanque con lote ACTIVO debe permanecer en estado OCUPADO' USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_estado_estanque_operativo$;

DROP TRIGGER IF EXISTS trg_validar_estado_estanque_operativo ON biofloc.estanques;
CREATE TRIGGER trg_validar_estado_estanque_operativo
BEFORE INSERT OR UPDATE OF estado_id, activo ON biofloc.estanques
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_estado_estanque_operativo();

    
-- Los nombres de estados de lote/estanque son claves semánticas para las reglas
-- operativas y no deben reinterpretarse después de existir en el sistema.
CREATE OR REPLACE FUNCTION biofloc.proteger_catalogos_estados_operativos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_proteger_catalogos_estados_operativos$
BEGIN
    IF TG_TABLE_NAME = 'estados_lote' AND NEW.nombre IS DISTINCT FROM OLD.nombre THEN
        IF OLD.nombre IN ('PLANIFICADO', 'ACTIVO', 'FINALIZADO', 'CANCELADO')
           OR EXISTS (SELECT 1 FROM biofloc.lotes WHERE estado_id = OLD.id)
        THEN
            RAISE EXCEPTION 'El estado de lote % es semántico o tiene historial y no puede renombrarse',
                OLD.nombre USING ERRCODE='check_violation';
        END IF;
    END IF;

    IF TG_TABLE_NAME = 'estados_estanque' AND NEW.nombre IS DISTINCT FROM OLD.nombre THEN
        IF OLD.nombre IN ('DISPONIBLE', 'OCUPADO', 'MANTENIMIENTO', 'FUERA_DE_SERVICIO')
           OR EXISTS (SELECT 1 FROM biofloc.estanques WHERE estado_id = OLD.id)
        THEN
            RAISE EXCEPTION 'El estado de estanque % es semántico o tiene historial y no puede renombrarse',
                OLD.nombre USING ERRCODE='check_violation';
        END IF;
    END IF;

    IF TG_TABLE_NAME = 'estados_lote' AND NEW.activo IS DISTINCT FROM OLD.activo
       AND NEW.activo = FALSE
       AND EXISTS (
           SELECT 1 FROM biofloc.lotes l
           WHERE l.estado_id = OLD.id
             AND l.fecha_cierre IS NULL
       )
    THEN
        RAISE EXCEPTION 'No se puede desactivar un estado de lote utilizado por lotes sin cierre'
            USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'estados_estanque' AND NEW.activo IS DISTINCT FROM OLD.activo
       AND NEW.activo = FALSE
       AND EXISTS (
           SELECT 1 FROM biofloc.estanques e
           WHERE e.estado_id = OLD.id
             AND e.activo = TRUE
       )
    THEN
        RAISE EXCEPTION 'No se puede desactivar un estado de estanque utilizado por estanques activos'
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_proteger_catalogos_estados_operativos$;

DROP TRIGGER IF EXISTS trg_proteger_catalogos_estados_lote ON biofloc.estados_lote;
CREATE TRIGGER trg_proteger_catalogos_estados_lote
BEFORE UPDATE OF nombre, activo ON biofloc.estados_lote
FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_catalogos_estados_operativos();

DROP TRIGGER IF EXISTS trg_proteger_catalogos_estados_estanque ON biofloc.estados_estanque;
CREATE TRIGGER trg_proteger_catalogos_estados_estanque
BEFORE UPDATE OF nombre, activo ON biofloc.estados_estanque
FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_catalogos_estados_operativos();


-- Un lote ACTIVO solo puede ocupar un estanque operativo.
-- Comparte el mismo bloqueo transaccional por estanque con la validación de
-- estado del estanque para cerrar la carrera entre ambas operaciones.
CREATE OR REPLACE FUNCTION biofloc.validar_lote_estanque_operativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_lote_estanque_operativo$
DECLARE
    v_estado_lote TEXT;
    v_estado_estanque TEXT;
    v_estanque_activo BOOLEAN;
BEGIN
    SELECT nombre INTO v_estado_lote
    FROM biofloc.estados_lote
    WHERE id = NEW.estado_id;

    IF v_estado_lote <> 'ACTIVO' THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(2147483000, NEW.estanque_id);

    SELECT e.activo, ee.nombre
      INTO v_estanque_activo, v_estado_estanque
    FROM biofloc.estanques e
    JOIN biofloc.estados_estanque ee ON ee.id = e.estado_id
    WHERE e.id = NEW.estanque_id;

    IF v_estanque_activo IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'Un lote ACTIVO no puede ocupar un estanque inactivo'
            USING ERRCODE='check_violation';
    END IF;

    IF v_estado_estanque <> 'OCUPADO' THEN
        RAISE EXCEPTION
            'Un lote ACTIVO solo puede ocupar un estanque en estado OCUPADO; estado actual: %',
            v_estado_estanque
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_validar_lote_estanque_operativo$;

DROP TRIGGER IF EXISTS trg_validar_lote_estanque_operativo ON biofloc.lotes;
CREATE TRIGGER trg_validar_lote_estanque_operativo
BEFORE INSERT OR UPDATE OF estanque_id, estado_id
ON biofloc.lotes
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_lote_estanque_operativo();


-- La fecha de siembra es una referencia histórica base del lote.
-- Una vez iniciado/cerrado el historial no puede reinterpretarse.
CREATE OR REPLACE FUNCTION biofloc.proteger_fecha_siembra_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_proteger_fecha_siembra_historica$
BEGIN
    IF NEW.fecha_siembra IS DISTINCT FROM OLD.fecha_siembra
       AND (
           OLD.fecha_cierre IS NOT NULL
           OR EXISTS (SELECT 1 FROM biofloc.biometrias WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.mortalidades WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.cosechas WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.alimentaciones WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.mediciones_biofloc WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.mediciones_agua WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.aplicaciones_biofloc WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.gastos WHERE lote_id = OLD.id)
           OR EXISTS (SELECT 1 FROM biofloc.detalles_venta WHERE lote_id = OLD.id)
       )
    THEN
        RAISE EXCEPTION
            'La fecha de siembra del lote % es inmutable una vez iniciado o cerrado su historial',
            OLD.id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_proteger_fecha_siembra_historica$;

DROP TRIGGER IF EXISTS trg_proteger_fecha_siembra_historica ON biofloc.lotes;
CREATE TRIGGER trg_proteger_fecha_siembra_historica
BEFORE UPDATE OF fecha_siembra ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_fecha_siembra_historica();


-- Un movimiento histórico no puede dejar existencias negativas en ningún punto
-- posterior de la línea temporal del producto.
CREATE OR REPLACE FUNCTION biofloc.validar_stock_historico_no_negativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_stock_historico_no_negativo$
DECLARE
    v_stock NUMERIC := 0;
    v_efecto INTEGER;
    v_row RECORD;
BEGIN
    FOR v_row IN
        SELECT
            mi.cantidad,
            CASE
                WHEN tm.nombre = 'AJUSTE' THEN mi.efecto_stock
                ELSE tm.afecta_stock
            END AS efecto
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.tipos_movimiento_inventario tm ON tm.id = mi.tipo_movimiento_id
        WHERE mi.producto_id = NEW.producto_id
        ORDER BY mi.fecha_hora ASC, mi.id ASC
    LOOP
        v_efecto := v_row.efecto;
        v_stock := v_stock + (v_row.cantidad * v_efecto);
        IF v_stock < 0 THEN
            RAISE EXCEPTION
                'El movimiento del producto % dejaría stock negativo en algún punto de su historia',
                NEW.producto_id USING ERRCODE='check_violation';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$fn_validar_stock_historico_no_negativo$;

DROP TRIGGER IF EXISTS trg_validar_stock_historico_no_negativo ON biofloc.movimientos_inventario;
CREATE CONSTRAINT TRIGGER trg_validar_stock_historico_no_negativo
AFTER INSERT ON biofloc.movimientos_inventario
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_stock_historico_no_negativo();
