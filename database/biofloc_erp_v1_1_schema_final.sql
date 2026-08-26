-- BIOFLOC ERP V1.1 — Schema corregido y revisado
-- ============================================================
-- BIOFLOC ERP V1 - PostgreSQL
-- Sistema de gestión para producción de tilapia roja en Biofloc
-- 43 tablas | 3 vistas | V1.1
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS biofloc;
SET search_path TO biofloc, public;

-- ============================================================
-- 1. SEGURIDAD
-- ============================================================

CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE usuarios (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol_id BIGINT NOT NULL REFERENCES roles(id),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. CATÁLOGOS PRODUCTIVOS
-- ============================================================

CREATE TABLE especies (
    id BIGSERIAL PRIMARY KEY,
    nombre_comun VARCHAR(100) NOT NULL UNIQUE,
    nombre_cientifico VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE etapas_productivas (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    orden SMALLINT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (orden > 0)
);

CREATE TABLE estados_estanque (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(40) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE estados_lote (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(40) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- 3. INFRAESTRUCTURA Y LOTES
-- ============================================================

-- ============================================================
--  REFERENCIAS DE PRODUCCIÓN
--  Valores esperados por especie y etapa para comparar desempeño real.
-- ============================================================

CREATE TABLE referencias_produccion (
    id                  BIGSERIAL PRIMARY KEY,
    especie_id          BIGINT NOT NULL REFERENCES especies(id),
    etapa_productiva_id BIGINT NOT NULL REFERENCES etapas_productivas(id),
    semana_desde        INTEGER NOT NULL CHECK (semana_desde >= 0),
    semana_hasta        INTEGER NOT NULL CHECK (semana_hasta >= semana_desde),
    peso_esperado_g     NUMERIC(10,2) CHECK (peso_esperado_g >= 0),
    tasa_alimentacion_pct NUMERIC(6,3) CHECK (tasa_alimentacion_pct >= 0),
    raciones_min        INTEGER CHECK (raciones_min IS NULL OR raciones_min >= 0),
    raciones_max        INTEGER,
    fase                VARCHAR(40),
    observaciones       TEXT,
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (especie_id, etapa_productiva_id, semana_desde, semana_hasta),
    CHECK (raciones_max IS NULL OR raciones_min IS NULL OR raciones_max >= raciones_min),
    CHECK (fase IS NULL OR fase IN ('Inicio', 'Levante', 'Engorde'))
);

COMMENT ON COLUMN referencias_produccion.raciones_min IS
    'Mínimo de raciones/día. Un rango 6–8 se guarda como min=6 max=8; no se promedia.';
COMMENT ON COLUMN referencias_produccion.fase IS
    'Fase de alimentación (Inicio/Levante/Engorde). Independiente de etapas_productivas.';



CREATE TABLE estanques (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    diametro NUMERIC(8,2) NOT NULL,
    profundidad NUMERIC(8,2) NOT NULL,
    estado_id BIGINT NOT NULL REFERENCES estados_estanque(id),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (diametro > 0),
    CHECK (profundidad > 0)
);

CREATE TABLE lotes (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    estanque_id BIGINT NOT NULL REFERENCES estanques(id),
    especie_id BIGINT NOT NULL REFERENCES especies(id),
    etapa_productiva_id BIGINT NOT NULL REFERENCES etapas_productivas(id),
    estado_id BIGINT NOT NULL REFERENCES estados_lote(id),
    fecha_siembra DATE NOT NULL,
    fecha_cierre DATE,
    cantidad_sembrada INTEGER NOT NULL,
    peso_inicial_promedio_g NUMERIC(10,3),
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad_sembrada > 0),
    CHECK (peso_inicial_promedio_g IS NULL OR peso_inicial_promedio_g >= 0),
    CHECK (fecha_cierre IS NULL OR fecha_cierre >= fecha_siembra)
);

COMMENT ON COLUMN lotes.peso_inicial_promedio_g IS
    'Peso promedio individual de los peces al momento de la siembra, en gramos (g).';

-- ============================================================
-- 4. PRODUCCIÓN
-- ============================================================

CREATE TABLE biometrias (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    cantidad_muestra INTEGER NOT NULL,
    peso_total_muestra_g NUMERIC(12,3) NOT NULL,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    talla_promedio       NUMERIC(10,2) CHECK (talla_promedio >= 0),
    unidad_talla         VARCHAR(20),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad_muestra > 0),
    CHECK (peso_total_muestra_g > 0)
);

COMMENT ON COLUMN biometrias.peso_total_muestra_g IS
    'Peso total de la muestra biometrada, en gramos (g). peso_total_muestra_g / cantidad_muestra = peso promedio por pez en gramos.';

CREATE TABLE mortalidades (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    cantidad INTEGER NOT NULL,
    causa VARCHAR(150),
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad > 0)
);

CREATE TABLE cosechas (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    cantidad_peces INTEGER NOT NULL,
    peso_total_kg NUMERIC(12,3) NOT NULL,
    peso_promedio_g NUMERIC(10,3),
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (peso_total_kg > 0),
    CHECK (cantidad_peces > 0),
    CHECK (peso_promedio_g IS NULL OR peso_promedio_g >= 0)
);

COMMENT ON COLUMN cosechas.peso_total_kg IS
    'Peso total cosechado, en kilogramos (kg).';
COMMENT ON COLUMN cosechas.peso_promedio_g IS
    'Peso promedio individual de los peces cosechados, en gramos (g).';

-- ============================================================
-- 5. AGUA
-- ============================================================

CREATE TABLE parametros_agua (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    unidad VARCHAR(30) NOT NULL,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE mediciones_agua (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    parametro_id BIGINT NOT NULL REFERENCES parametros_agua(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    valor NUMERIC(12,4) NOT NULL,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valor >= 0)
);

CREATE TABLE referencias_agua (
    id BIGSERIAL PRIMARY KEY,
    especie_id BIGINT NOT NULL REFERENCES especies(id),
    etapa_productiva_id BIGINT NOT NULL REFERENCES etapas_productivas(id),
    parametro_id BIGINT NOT NULL REFERENCES parametros_agua(id),
    valor_minimo NUMERIC(12,4),
    valor_maximo NUMERIC(12,4),
    observaciones TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (
        valor_minimo IS NULL
        OR valor_maximo IS NULL
        OR valor_minimo <= valor_maximo
    ),
    UNIQUE (especie_id, etapa_productiva_id, parametro_id)
);

-- ============================================================
-- 6. BIOFLOC
-- ============================================================

CREATE TABLE tipos_aplicacion_biofloc (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE aplicaciones_biofloc (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    tipo_aplicacion_id BIGINT NOT NULL REFERENCES tipos_aplicacion_biofloc(id),
    producto_id BIGINT,
    fecha_hora TIMESTAMPTZ NOT NULL,
    cantidad NUMERIC(12,4),
    unidad VARCHAR(30),
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad IS NULL OR cantidad >= 0)
);

CREATE TABLE mediciones_biofloc (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    volumen_sedimentable NUMERIC(10,2) NOT NULL,
    unidad VARCHAR(20) NOT NULL DEFAULT 'mL/L',
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    relacion_cn         NUMERIC(10,3) CHECK (relacion_cn >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (volumen_sedimentable >= 0)
);

CREATE TABLE referencias_biofloc (
    id BIGSERIAL PRIMARY KEY,
    especie_id BIGINT NOT NULL REFERENCES especies(id),
    etapa_productiva_id BIGINT NOT NULL REFERENCES etapas_productivas(id),
    indicador VARCHAR(40) NOT NULL,
    valor_minimo NUMERIC(12,4),
    valor_objetivo NUMERIC(12,4),
    valor_maximo NUMERIC(12,4),
    unidad VARCHAR(30),
    observaciones TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (indicador IN ('VOLUMEN_SEDIMENTABLE', 'RELACION_CN')),
    CHECK (
        valor_minimo IS NULL
        OR valor_maximo IS NULL
        OR valor_minimo <= valor_maximo
    ),
    CHECK (
        valor_objetivo IS NULL
        OR valor_minimo IS NULL
        OR valor_objetivo >= valor_minimo
    ),
    CHECK (
        valor_objetivo IS NULL
        OR valor_maximo IS NULL
        OR valor_objetivo <= valor_maximo
    ),
    UNIQUE (especie_id, etapa_productiva_id, indicador)
);

COMMENT ON TABLE referencias_biofloc IS
    'Rangos y objetivo de Biofloc por especie y etapa. Los valores los digita el administrador; no hay semilla.';
COMMENT ON COLUMN referencias_biofloc.indicador IS
    'VOLUMEN_SEDIMENTABLE o RELACION_CN, alineado a mediciones_biofloc.';

-- ============================================================
-- 7. INVENTARIO
-- ============================================================

CREATE TABLE categorias_inventario (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE unidades (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    simbolo VARCHAR(10) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE productos (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    categoria_id BIGINT NOT NULL REFERENCES categorias_inventario(id),
    unidad_id BIGINT NOT NULL REFERENCES unidades(id),
    stock_minimo NUMERIC(12,3) NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (stock_minimo >= 0)
);

CREATE TABLE tipos_movimiento_inventario (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    afecta_stock SMALLINT NOT NULL,
    CHECK (afecta_stock IN (-1, 1))
);

CREATE TABLE movimientos_inventario (
    id BIGSERIAL PRIMARY KEY,
    producto_id BIGINT NOT NULL REFERENCES productos(id),
    tipo_movimiento_id BIGINT NOT NULL REFERENCES tipos_movimiento_inventario(id),
    cantidad NUMERIC(12,3) NOT NULL,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    referencia_tipo VARCHAR(40),
    referencia_id BIGINT,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    costo_unitario       NUMERIC(14,2) CHECK (costo_unitario >= 0),
    costo_total          NUMERIC(16,2) CHECK (costo_total >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad > 0)
);

-- Alimentación depende de productos
CREATE TABLE alimentaciones (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes(id),
    producto_id BIGINT NOT NULL REFERENCES productos(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    cantidad NUMERIC(12,3) NOT NULL,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad > 0)
);

-- Ahora sí podemos completar la relación Biofloc -> producto
ALTER TABLE aplicaciones_biofloc
    ADD CONSTRAINT fk_aplicacion_producto
    FOREIGN KEY (producto_id) REFERENCES productos(id);

-- ============================================================
-- 8. COMPRAS
-- ============================================================

CREATE TABLE compras (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    proveedor VARCHAR(150),
    total NUMERIC(14,2) NOT NULL DEFAULT 0,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (total >= 0)
);

CREATE TABLE detalles_compra (
    id BIGSERIAL PRIMARY KEY,
    compra_id BIGINT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES productos(id),
    cantidad NUMERIC(12,3) NOT NULL,
    precio_unitario NUMERIC(14,2) NOT NULL,
    subtotal NUMERIC(14,2) NOT NULL,
    CHECK (cantidad > 0),
    CHECK (precio_unitario >= 0),
    CHECK (subtotal >= 0)
);

-- ============================================================
-- 9. FINANZAS
-- ============================================================

CREATE TABLE categorias_gasto (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE gastos (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    categoria_id BIGINT NOT NULL REFERENCES categorias_gasto(id),
    lote_id BIGINT REFERENCES lotes(id),
    descripcion VARCHAR(250) NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    proveedor VARCHAR(150),
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valor > 0)
);

CREATE TABLE ventas (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    cliente VARCHAR(150),
    total NUMERIC(14,2) NOT NULL DEFAULT 0,
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (total >= 0)
);

CREATE TABLE detalles_venta (
    id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    cantidad NUMERIC(12,3) NOT NULL,
    precio_unitario NUMERIC(14,2) NOT NULL,
    subtotal NUMERIC(14,2) NOT NULL,
    CHECK (cantidad > 0),
    CHECK (precio_unitario >= 0),
    CHECK (subtotal >= 0),
    lote_id              BIGINT NOT NULL REFERENCES lotes(id)
);

-- ============================================================
-- 10. EQUIPOS
-- ============================================================

CREATE TABLE tipos_equipo (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE estados_equipo (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE equipos (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    tipo_equipo_id BIGINT NOT NULL REFERENCES tipos_equipo(id),
    estado_id BIGINT NOT NULL REFERENCES estados_equipo(id),
    marca VARCHAR(80),
    modelo VARCHAR(80),
    numero_serie VARCHAR(100),
    fecha_adquisicion DATE,
    valor_adquisicion NUMERIC(14,2),
    ubicacion VARCHAR(150),
    observaciones TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valor_adquisicion IS NULL OR valor_adquisicion >= 0)
);

CREATE TABLE tipos_mantenimiento (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE mantenimientos (
    id BIGSERIAL PRIMARY KEY,
    equipo_id BIGINT NOT NULL REFERENCES equipos(id),
    tipo_mantenimiento_id BIGINT NOT NULL REFERENCES tipos_mantenimiento(id),
    fecha DATE NOT NULL,
    descripcion VARCHAR(250) NOT NULL,
    costo NUMERIC(14,2) NOT NULL DEFAULT 0,
    proveedor VARCHAR(150),
    observaciones TEXT,
    registrado_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (costo >= 0)
);

CREATE TABLE fallas (
    id BIGSERIAL PRIMARY KEY,
    equipo_id BIGINT NOT NULL REFERENCES equipos(id),
    fecha_hora TIMESTAMPTZ NOT NULL,
    descripcion VARCHAR(250) NOT NULL,
    impacto VARCHAR(100),
    solucion TEXT,
    costo NUMERIC(14,2) NOT NULL DEFAULT 0,
    registrada_por BIGINT NOT NULL REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (costo >= 0)
);

-- ============================================================
-- 11. ENERGÍA
-- ============================================================

CREATE TABLE eventos_energia (
    id BIGSERIAL PRIMARY KEY,
    fecha_hora_inicio TIMESTAMPTZ NOT NULL,
    fecha_hora_fin TIMESTAMPTZ,
    duracion_minutos INTEGER,
    tipo VARCHAR(50) NOT NULL DEFAULT 'CORTE',
    respaldo_activado BOOLEAN NOT NULL DEFAULT FALSE,
    equipo_respaldo_id BIGINT REFERENCES equipos(id),
    observaciones TEXT,
    registrado_por BIGINT REFERENCES usuarios(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (fecha_hora_fin IS NULL OR fecha_hora_fin >= fecha_hora_inicio),
    CHECK (duracion_minutos IS NULL OR duracion_minutos >= 0),
    CHECK (
        (respaldo_activado = FALSE)
        OR equipo_respaldo_id IS NOT NULL
    )
);

-- ============================================================
-- 12. ALARMAS
-- ============================================================

CREATE TABLE tipos_alarma (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE niveles_alarma (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    prioridad SMALLINT NOT NULL,
    CHECK (prioridad > 0)
);

CREATE TABLE estados_alarma (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(100)
);

CREATE TABLE alarmas (
    id BIGSERIAL PRIMARY KEY,
    tipo_alarma_id BIGINT NOT NULL REFERENCES tipos_alarma(id),
    nivel_alarma_id BIGINT NOT NULL REFERENCES niveles_alarma(id),
    estado_alarma_id BIGINT NOT NULL REFERENCES estados_alarma(id),
    lote_id BIGINT REFERENCES lotes(id),
    equipo_id BIGINT REFERENCES equipos(id),
    evento_energia_id BIGINT REFERENCES eventos_energia(id),
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    titulo VARCHAR(150) NOT NULL,
    mensaje TEXT NOT NULL,
    atendida_por BIGINT REFERENCES usuarios(id),
    fecha_atencion TIMESTAMPTZ,
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        fecha_atencion IS NULL
        OR fecha_atencion >= fecha_hora
    )
);

-- ============================================================
-- 13. AUDITORÍA
-- ============================================================

CREATE TABLE auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id),
    tabla VARCHAR(100) NOT NULL,
    registro_id BIGINT NOT NULL,
    accion VARCHAR(20) NOT NULL,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detalle JSONB,
    CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- ============================================================
-- 14. ÍNDICES
-- ============================================================

CREATE INDEX idx_lotes_estanque
    ON lotes(estanque_id);

CREATE INDEX idx_lotes_estado
    ON lotes(estado_id);

CREATE INDEX idx_lotes_especie
    ON lotes(especie_id);

CREATE INDEX idx_biometrias_lote_fecha
    ON biometrias(lote_id, fecha_hora);

CREATE INDEX idx_mortalidades_lote_fecha
    ON mortalidades(lote_id, fecha_hora);

CREATE INDEX idx_alimentaciones_lote_fecha
    ON alimentaciones(lote_id, fecha_hora);

CREATE INDEX idx_alimentaciones_producto
    ON alimentaciones(producto_id);

CREATE INDEX idx_mediciones_agua_lote_fecha
    ON mediciones_agua(lote_id, fecha_hora);

CREATE INDEX idx_mediciones_agua_parametro
    ON mediciones_agua(parametro_id);

CREATE INDEX idx_aplicaciones_biofloc_lote_fecha
    ON aplicaciones_biofloc(lote_id, fecha_hora);

CREATE INDEX idx_mediciones_biofloc_lote_fecha
    ON mediciones_biofloc(lote_id, fecha_hora);

CREATE INDEX idx_referencias_biofloc_especie_etapa
    ON referencias_biofloc(especie_id, etapa_productiva_id);

CREATE INDEX idx_movimientos_producto_fecha
    ON movimientos_inventario(producto_id, fecha_hora);

CREATE INDEX idx_compras_fecha
    ON compras(fecha);

CREATE INDEX idx_gastos_fecha
    ON gastos(fecha);

CREATE INDEX idx_gastos_lote
    ON gastos(lote_id);

CREATE INDEX idx_ventas_fecha
    ON ventas(fecha);

CREATE INDEX idx_detalles_venta_lote
    ON detalles_venta(lote_id);

CREATE INDEX idx_mantenimientos_equipo_fecha
    ON mantenimientos(equipo_id, fecha);

CREATE INDEX idx_fallas_equipo_fecha
    ON fallas(equipo_id, fecha_hora);

CREATE INDEX idx_eventos_energia_fecha
    ON eventos_energia(fecha_hora_inicio);

CREATE INDEX idx_alarmas_fecha
    ON alarmas(fecha_hora);

CREATE INDEX idx_alarmas_estado
    ON alarmas(estado_alarma_id);

CREATE INDEX idx_auditoria_tabla_registro
    ON auditoria(tabla, registro_id);

CREATE INDEX idx_auditoria_usuario_fecha
    ON auditoria(usuario_id, fecha_hora);

-- ============================================================
-- 15. TRIGGER: updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION actualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_referencias_produccion_updated_at
BEFORE UPDATE ON referencias_produccion
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_usuarios_updated_at
BEFORE UPDATE ON usuarios
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_estanques_updated_at
BEFORE UPDATE ON estanques
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_lotes_updated_at
BEFORE UPDATE ON lotes
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_productos_updated_at
BEFORE UPDATE ON productos
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_equipos_updated_at
BEFORE UPDATE ON equipos
FOR EACH ROW
EXECUTE FUNCTION actualizar_updated_at();

-- ============================================================
-- 16. TRIGGER: un solo lote ACTIVO por estanque
-- Usa bloqueo transaccional por estanque para evitar carreras
-- entre dos operaciones concurrentes.
-- ============================================================

CREATE OR REPLACE FUNCTION validar_lote_activo()
RETURNS TRIGGER AS $$
DECLARE
    es_activo BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM estados_lote
        WHERE id = NEW.estado_id
          AND nombre = 'ACTIVO'
    )
    INTO es_activo;

    IF es_activo THEN
        PERFORM pg_advisory_xact_lock(2147483000, NEW.estanque_id);

        IF EXISTS (
            SELECT 1
            FROM lotes l
            JOIN estados_lote e
              ON e.id = l.estado_id
            WHERE l.estanque_id = NEW.estanque_id
              AND e.nombre = 'ACTIVO'
              AND l.id <> NEW.id
        ) THEN
            RAISE EXCEPTION
                'El estanque % ya tiene un lote activo.',
                NEW.estanque_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_lote_activo
BEFORE INSERT OR UPDATE OF estanque_id, estado_id ON lotes
FOR EACH ROW
EXECUTE FUNCTION validar_lote_activo();

-- ============================================================
-- 17. VISTA: STOCK
-- ============================================================

CREATE OR REPLACE VIEW vista_stock_productos AS
SELECT
    p.id AS producto_id,
    p.codigo,
    p.nombre,
    u.simbolo AS unidad,
    COALESCE(
        SUM(mi.cantidad * tmi.afecta_stock),
        0
    ) AS stock_actual,
    p.stock_minimo
FROM productos p
JOIN unidades u
  ON u.id = p.unidad_id
LEFT JOIN movimientos_inventario mi
  ON mi.producto_id = p.id
LEFT JOIN tipos_movimiento_inventario tmi
  ON tmi.id = mi.tipo_movimiento_id
GROUP BY
    p.id,
    p.codigo,
    p.nombre,
    u.simbolo,
    p.stock_minimo;

-- ============================================================
-- 18. VISTA: POBLACIÓN ESTIMADA
-- ============================================================

CREATE OR REPLACE VIEW vista_biomasa_lotes AS
SELECT
    l.id AS lote_id,
    l.codigo,
    l.cantidad_sembrada,

    COALESCE(
        (
            SELECT SUM(m.cantidad)
            FROM mortalidades m
            WHERE m.lote_id = l.id
        ),
        0
    ) AS mortalidad_acumulada,

    COALESCE(
        (
            SELECT SUM(c.cantidad_peces)
            FROM cosechas c
            WHERE c.lote_id = l.id
        ),
        0
    ) AS peces_cosechados,

    (
        l.cantidad_sembrada
        - COALESCE(
            (
                SELECT SUM(m.cantidad)
                FROM mortalidades m
                WHERE m.lote_id = l.id
            ),
            0
        )
        - COALESCE(
            (
                SELECT SUM(c.cantidad_peces)
                FROM cosechas c
                WHERE c.lote_id = l.id
            ),
            0
        )
    ) AS poblacion_estimada

FROM lotes l;

-- ============================================================
-- 19. VISTA: ÚLTIMA BIOMETRÍA
-- ============================================================

CREATE OR REPLACE VIEW vista_ultima_biometria AS
SELECT DISTINCT ON (lote_id)
    lote_id,
    fecha_hora,
    cantidad_muestra,
    peso_total_muestra_g,
    ROUND(
        peso_total_muestra_g / NULLIF(cantidad_muestra, 0),
        3
    ) AS peso_promedio_g
FROM biometrias
ORDER BY lote_id, fecha_hora DESC;

-- ============================================================
-- 21. DATOS INICIALES
-- ============================================================

INSERT INTO roles (nombre, descripcion)
VALUES
    ('ADMINISTRADOR', 'Gestión general del sistema'),
    ('OPERARIO', 'Registro de operaciones diarias'),
    ('TECNICO', 'Control técnico y productivo');

INSERT INTO especies (nombre_comun, nombre_cientifico)
VALUES
    ('Tilapia roja', 'Oreochromis spp.');

INSERT INTO etapas_productivas (nombre, descripcion, orden)
VALUES
    ('Alevinaje', 'Etapa inicial del cultivo', 1),
    ('Preengorde', 'Etapa intermedia de crecimiento', 2),
    ('Engorde', 'Etapa final hasta cosecha', 3);

INSERT INTO estados_estanque (nombre, descripcion)
VALUES
    ('DISPONIBLE', 'Estanque disponible para producción'),
    ('OCUPADO', 'Estanque actualmente ocupado'),
    ('MANTENIMIENTO', 'Estanque en mantenimiento'),
    ('FUERA_DE_SERVICIO', 'Estanque no disponible');

INSERT INTO estados_lote (nombre, descripcion)
VALUES
    ('PLANIFICADO', 'Lote planificado pero no iniciado'),
    ('ACTIVO', 'Lote actualmente en producción'),
    ('FINALIZADO', 'Lote terminado'),
    ('CANCELADO', 'Lote cancelado');

INSERT INTO parametros_agua (nombre, unidad, descripcion)
VALUES
    ('Oxígeno disuelto', 'mg/L', 'Oxígeno disuelto en el agua'),
    ('Temperatura', '°C', 'Temperatura del agua'),
    ('pH', 'pH', 'Potencial de hidrógeno'),
    ('Alcalinidad', 'mg/L CaCO3', 'Alcalinidad del agua'),
    ('Amonio', 'mg/L', 'Concentración de amonio'),
    ('Nitrito', 'mg/L', 'Concentración de nitrito');

INSERT INTO tipos_aplicacion_biofloc (nombre, descripcion)
VALUES
    ('FUENTE_CARBONO', 'Aplicación de fuente de carbono'),
    ('PROBIOTICO', 'Aplicación de probióticos'),
    ('CORRECTIVO', 'Aplicación de correctivos'),
    ('PURGA', 'Extracción de sólidos o agua del sistema');

INSERT INTO categorias_inventario (nombre, descripcion)
VALUES
    ('ALIMENTO', 'Alimentos para los peces'),
    ('FUENTE_CARBONO', 'Fuentes de carbono para Biofloc'),
    ('PROBIOTICO', 'Productos probióticos'),
    ('CORRECTIVO', 'Productos utilizados para corrección del sistema'),
    ('OTRO', 'Otros insumos productivos');

INSERT INTO unidades (nombre, simbolo)
VALUES
    ('Kilogramo', 'kg'),
    ('Gramo', 'g'),
    ('Litro', 'L'),
    ('Mililitro', 'mL'),
    ('Unidad', 'und');

INSERT INTO tipos_movimiento_inventario
    (nombre, descripcion, afecta_stock)
VALUES
    ('ENTRADA', 'Entrada de producto al inventario', 1),
    ('SALIDA', 'Salida de producto del inventario', -1);

INSERT INTO categorias_gasto (nombre, descripcion)
VALUES
    ('SERVICIOS', 'Agua, energía, internet y otros servicios'),
    ('TRANSPORTE', 'Transporte y logística'),
    ('MANTENIMIENTO', 'Mantenimiento de infraestructura y equipos'),
    ('MANO_DE_OBRA', 'Costos de personal y mano de obra'),
    ('ADMINISTRATIVO', 'Gastos administrativos'),
    ('COMERCIAL', 'Gastos asociados a comercialización'),
    ('OTROS', 'Otros gastos');

INSERT INTO tipos_equipo (nombre, descripcion)
VALUES
    ('BLOWER', 'Equipo de aireación'),
    ('BOMBA', 'Bomba de agua'),
    ('PLANTA_ELECTRICA', 'Generador eléctrico de respaldo'),
    ('AIREADOR', 'Equipo de aireación adicional'),
    ('OTRO', 'Otro equipo productivo');

INSERT INTO estados_equipo (nombre, descripcion)
VALUES
    ('OPERATIVO', 'Equipo en funcionamiento'),
    ('MANTENIMIENTO', 'Equipo en mantenimiento'),
    ('FUERA_DE_SERVICIO', 'Equipo no operativo'),
    ('BAJA', 'Equipo retirado');

INSERT INTO tipos_mantenimiento (nombre, descripcion)
VALUES
    ('PREVENTIVO', 'Mantenimiento programado'),
    ('CORRECTIVO', 'Mantenimiento por falla o avería');

INSERT INTO tipos_alarma (nombre, descripcion)
VALUES
    ('CORTE_ELECTRICO', 'Interrupción del suministro eléctrico'),
    ('PARAMETRO_AGUA', 'Parámetro del agua fuera de referencia'),
    ('NIVEL_BIOFLOC', 'Nivel de floc fuera del rango configurado'),
    ('EQUIPO', 'Evento relacionado con un equipo'),
    ('INVENTARIO_BAJO', 'Producto por debajo del stock mínimo');

INSERT INTO niveles_alarma (nombre, prioridad)
VALUES
    ('BAJA', 1),
    ('MEDIA', 2),
    ('ALTA', 3),
    ('CRITICA', 4);

INSERT INTO estados_alarma (nombre, descripcion)
VALUES
    ('PENDIENTE', 'Alarma pendiente de atención'),
    ('ATENDIDA', 'Alarma atendida'),
    ('CERRADA', 'Alarma cerrada');

-- ============================================================
-- FIN
-- ============================================================

COMMIT;
