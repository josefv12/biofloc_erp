-- Corrige el bloqueo transaccional del estanque.
CREATE OR REPLACE FUNCTION biofloc.validar_lote_activo()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE es_activo BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM biofloc.estados_lote WHERE id=NEW.estado_id AND nombre='ACTIVO') INTO es_activo;
    IF es_activo THEN
        PERFORM pg_advisory_xact_lock(NEW.estanque_id);
        IF EXISTS (
            SELECT 1 FROM biofloc.lotes l
            JOIN biofloc.estados_lote e ON e.id=l.estado_id
            WHERE l.estanque_id=NEW.estanque_id AND e.nombre='ACTIVO' AND l.id<>NEW.id
        ) THEN
            RAISE EXCEPTION 'El estanque % ya tiene un lote activo.',NEW.estanque_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
