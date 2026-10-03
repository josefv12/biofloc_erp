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
    semana_desde        INTEGER NOT NULL CHECK (semana_desde >= 1),
    semana_hasta        INTEGER NOT NULL CHECK (semana_hasta >= semana_desde),
    peso_esperado_g     NUMERIC(10,2) CHECK (peso_esperado_g >= 0),
    tasa_alimentacion_pct NUMERIC(6,3) CHECK (tasa_alimentacion_pct >= 0),
    raciones_min        INTEGER CHECK (raciones_min IS NULL OR raciones_min > 0),
    raciones_max        INTEGER,
    fase                VARCHAR(40),
    observaciones       TEXT,
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (especie_id, etapa_productiva_id, semana_desde, semana_hasta),
    CHECK (raciones_max IS NULL OR (raciones_max > 0 AND (raciones_min IS NULL OR raciones_max >= raciones_min))),
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
    CHECK (
        (indicador = 'VOLUMEN_SEDIMENTABLE' AND unidad = 'mL/L')
        OR (indicador = 'RELACION_CN' AND unidad = 'C:N')
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
    efecto_stock         SMALLINT CHECK (efecto_stock IN (-1, 1)),
    costo_total          NUMERIC(16,2) CHECK (costo_total >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (cantidad > 0)
);

-- Alimentación depende de productos
-- Un registro operativo que consume inventario solo puede tener un movimiento automático.
CREATE UNIQUE INDEX uq_movimientos_inventario_alimentacion
    ON movimientos_inventario (referencia_tipo, referencia_id)
    WHERE referencia_tipo = 'ALIMENTACION'
      AND referencia_id IS NOT NULL;

CREATE UNIQUE INDEX uq_movimientos_inventario_aplicacion_biofloc
    ON movimientos_inventario (referencia_tipo, referencia_id)
    WHERE referencia_tipo = 'APLICACION_BIOFLOC'
      AND referencia_id IS NOT NULL;

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
RETURNS TRIGGER AS $fn_actualizar_updated_at$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$fn_actualizar_updated_at$;


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
RETURNS TRIGGER AS $fn_validar_lote_activo$
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
$fn_validar_lote_activo$;


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
        SUM(
            CASE
                WHEN tmi.nombre = 'AJUSTE' THEN mi.cantidad * mi.efecto_stock
                ELSE mi.cantidad * tmi.afecta_stock
            END
        ),
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
    ('SALIDA', 'Salida de producto del inventario', -1),
    ('AJUSTE', 'Ajuste manual de inventario con efecto positivo o negativo', 1);

INSERT INTO categorias_gasto (nombre, descripcion)
VALUES
    ('SERVICIOS', 'Agua, energía, internet y otros servicios'),
    ('TRANSPORTE', 'Transporte y logística'),
    ('MANTENIMIENTO', 'Mantenimiento de infraestructura y equipos'),
    ('MANO_DE_OBRA', 'Costos de personal y mano de obra'),
    ('ADMINISTRATIVO', 'Gastos administrativos'),
    ('COMERCIAL', 'Gastos asociados a comercialización'),
    ('OTROS', 'Otros gastos');
INSERT INTO categorias_gasto (nombre, descripcion) VALUES ('ALEVINOS', 'Compra de alevinos y material vivo de siembra');

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

    
-- Integridad productiva a nivel de base de datos.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_evento_lote()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_biofloc_validar_fecha_evento_lote$
DECLARE v_siembra DATE;
BEGIN
    SELECT fecha_siembra INTO v_siembra FROM lotes WHERE id=NEW.lote_id;
    IF v_siembra IS NULL THEN
        RAISE EXCEPTION 'Lote % no existe', NEW.lote_id USING ERRCODE='foreign_key_violation';
    END IF;
    IF NEW.fecha_hora < (v_siembra::timestamp AT TIME ZONE 'America/Bogota') THEN
        RAISE EXCEPTION 'La fecha del evento no puede ser anterior a la siembra del lote'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_biofloc_validar_fecha_evento_lote$;
CREATE TRIGGER trg_validar_fecha_biometria
BEFORE INSERT OR UPDATE ON biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();
CREATE TRIGGER trg_validar_fecha_mortalidad
BEFORE INSERT OR UPDATE ON mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();
CREATE TRIGGER trg_validar_fecha_cosecha
BEFORE INSERT OR UPDATE ON cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_lote();

CREATE OR REPLACE FUNCTION biofloc.validar_muestra_biometria()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_biofloc_validar_muestra_biometria$
DECLARE v_sembrados INTEGER; v_salidas INTEGER;
BEGIN
    SELECT cantidad_sembrada INTO v_sembrados FROM lotes WHERE id=NEW.lote_id;
    SELECT COALESCE(SUM(m.cantidad),0) INTO v_salidas
      FROM mortalidades m WHERE m.lote_id=NEW.lote_id AND m.fecha_hora<=NEW.fecha_hora;
    SELECT v_salidas + COALESCE(SUM(c.cantidad_peces),0) INTO v_salidas
      FROM cosechas c WHERE c.lote_id=NEW.lote_id AND c.fecha_hora<=NEW.fecha_hora;
    IF NEW.cantidad_muestra > GREATEST(v_sembrados-v_salidas,0) THEN
        RAISE EXCEPTION 'La muestra biométrica excede la población disponible. Disponible: %, solicitado: %',
            GREATEST(v_sembrados-v_salidas,0), NEW.cantidad_muestra USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_biofloc_validar_muestra_biometria$;
CREATE TRIGGER trg_validar_muestra_biometria
BEFORE INSERT OR UPDATE ON biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_muestra_biometria();

CREATE OR REPLACE FUNCTION biofloc.validar_promedio_cosecha()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_biofloc_validar_promedio_cosecha$
DECLARE v_esperado NUMERIC;
BEGIN
    v_esperado := (NEW.peso_total_kg * 1000) / NULLIF(NEW.cantidad_peces, 0);
    IF NEW.peso_promedio_g IS NOT NULL AND ABS(NEW.peso_promedio_g-v_esperado)>0.001 THEN
        RAISE EXCEPTION 'El peso promedio de la cosecha no coincide. Esperado: %, recibido: %',
            ROUND(v_esperado,3), NEW.peso_promedio_g USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_biofloc_validar_promedio_cosecha$;
CREATE TRIGGER trg_validar_promedio_cosecha
BEFORE INSERT OR UPDATE ON cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_promedio_cosecha();

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_evento_no_futura()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_biofloc_validar_fecha_evento_no_futura$
BEGIN
    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del evento no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END; $fn_biofloc_validar_fecha_evento_no_futura$;
CREATE TRIGGER trg_validar_fecha_biometria_futura BEFORE INSERT OR UPDATE ON biometrias
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_mortalidad_futura BEFORE INSERT OR UPDATE ON mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_cosecha_futura BEFORE INSERT OR UPDATE ON cosechas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_alimentacion_futura BEFORE INSERT OR UPDATE ON alimentaciones
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_medicion_biofloc_futura BEFORE INSERT OR UPDATE ON mediciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_medicion_agua_futura BEFORE INSERT OR UPDATE ON mediciones_agua
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();
CREATE TRIGGER trg_validar_fecha_aplicacion_biofloc_futura BEFORE INSERT OR UPDATE ON aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_evento_no_futura();


-- Integridad de inventario: tipos cerrados, ajustes direccionales,
-- entradas valoradas y prohibición de movimientos futuros.
CREATE OR REPLACE FUNCTION biofloc.validar_integridad_movimiento_inventario()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_biofloc_validar_integridad_movimiento_inventario$
DECLARE
    v_nombre VARCHAR(30);
    v_efecto SMALLINT;
    v_stock NUMERIC(18,3);
BEGIN
    SELECT nombre, afecta_stock
      INTO v_nombre, v_efecto
      FROM tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF v_nombre NOT IN ('ENTRADA', 'SALIDA', 'AJUSTE') THEN
        RAISE EXCEPTION 'Tipo de movimiento no permitido: %',
            COALESCE(v_nombre, NEW.tipo_movimiento_id::text)
            USING ERRCODE='check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' THEN
        IF NEW.efecto_stock IS NULL OR NEW.efecto_stock NOT IN (-1,1) THEN
            RAISE EXCEPTION 'AJUSTE requiere efecto_stock = 1 o -1'
                USING ERRCODE='check_violation';
        END IF;
        v_efecto := NEW.efecto_stock;
    ELSE
        IF NEW.efecto_stock IS NOT NULL THEN
            RAISE EXCEPTION '% no debe informar efecto_stock', v_nombre
                USING ERRCODE='check_violation';
        END IF;
    END IF;

    IF NEW.cantidad <= 0 THEN
        RAISE EXCEPTION 'La cantidad del movimiento debe ser mayor que cero'
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del movimiento de inventario no puede estar en el futuro'
            USING ERRCODE='check_violation';
    END IF;

    IF v_nombre = 'AJUSTE' AND NULLIF(BTRIM(NEW.observaciones), '') IS NULL THEN
        RAISE EXCEPTION 'AJUSTE requiere una observación que explique el motivo'
            USING ERRCODE='check_violation';
    END IF;

    IF v_efecto = 1 AND NEW.costo_unitario IS NULL THEN
        RAISE EXCEPTION '% positivo requiere costo_unitario', v_nombre
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_unitario < 0
       OR NEW.costo_total IS NOT NULL AND NEW.costo_total < 0 THEN
        RAISE EXCEPTION 'Los costos no pueden ser negativos'
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.costo_unitario IS NOT NULL AND NEW.costo_total IS NOT NULL
       AND ABS(NEW.costo_total - NEW.cantidad * NEW.costo_unitario) > 0.01 THEN
        RAISE EXCEPTION 'Costo total inconsistente con cantidad y costo unitario'
            USING ERRCODE='check_violation';
    END IF;

    IF v_efecto = -1 THEN
        PERFORM 1 FROM productos WHERE id=NEW.producto_id FOR UPDATE;

        SELECT COALESCE(SUM(
            CASE
                WHEN t.nombre='AJUSTE' THEN m.cantidad*m.efecto_stock
                ELSE m.cantidad*t.afecta_stock
            END
        ),0)
        INTO v_stock
        FROM movimientos_inventario m
        JOIN tipos_movimiento_inventario t ON t.id=m.tipo_movimiento_id
        WHERE m.producto_id=NEW.producto_id
          AND m.fecha_hora<=NEW.fecha_hora;

        IF v_stock < NEW.cantidad THEN
            RAISE EXCEPTION 'No hay stock suficiente en la fecha del movimiento. Disponible: %, solicitado: %',
                v_stock, NEW.cantidad USING ERRCODE='check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$fn_biofloc_validar_integridad_movimiento_inventario$;


CREATE TRIGGER trg_validar_integridad_movimiento_inventario
BEFORE INSERT OR UPDATE ON movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_integridad_movimiento_inventario();


-- Integridad: la unidad de un parámetro de agua queda inmutable tras la
-- primera medición, porque las mediciones históricas solo almacenan parametro_id.
CREATE OR REPLACE FUNCTION biofloc.validar_unidad_parametro_agua_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_unidad_parametro_agua_historica$
BEGIN
    IF NEW.unidad IS DISTINCT FROM OLD.unidad
       AND EXISTS (
           SELECT 1
           FROM biofloc.mediciones_agua
           WHERE parametro_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'No se puede cambiar la unidad del parámetro de agua % porque tiene mediciones históricas',
            OLD.id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_unidad_parametro_agua_historica$;

DROP TRIGGER IF EXISTS trg_validar_unidad_parametro_agua_historica
    ON biofloc.parametros_agua;

CREATE TRIGGER trg_validar_unidad_parametro_agua_historica
BEFORE UPDATE OF unidad ON biofloc.parametros_agua
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_unidad_parametro_agua_historica();



-- Integridad: las referencias Biofloc usan las mismas unidades canónicas
-- que las mediciones, evitando comparaciones numéricas incompatibles.
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



-- Integridad: una medición nueva solo puede usar un parámetro de agua activo.
CREATE OR REPLACE FUNCTION biofloc.validar_parametro_agua_activo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_parametro_agua_activo$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM biofloc.parametros_agua
        WHERE id = NEW.parametro_id
          AND activo = TRUE
    ) THEN
        RAISE EXCEPTION
            'El parámetro de agua % está inactivo y no admite nuevas mediciones',
            NEW.parametro_id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_parametro_agua_activo$;

DROP TRIGGER IF EXISTS trg_validar_parametro_agua_activo
    ON biofloc.mediciones_agua;

CREATE TRIGGER trg_validar_parametro_agua_activo
BEFORE INSERT OR UPDATE OF parametro_id ON biofloc.mediciones_agua
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_parametro_agua_activo();



-- Integridad: las alarmas no pueden retroceder en el flujo de atención.
CREATE OR REPLACE FUNCTION biofloc.validar_transicion_estado_alarma()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_transicion_estado_alarma$
DECLARE
    v_anterior VARCHAR(30);
    v_nuevo VARCHAR(30);
BEGIN
    SELECT nombre INTO v_anterior
    FROM biofloc.estados_alarma
    WHERE id = OLD.estado_alarma_id;

    SELECT nombre INTO v_nuevo
    FROM biofloc.estados_alarma
    WHERE id = NEW.estado_alarma_id;

    IF v_anterior IN ('PENDIENTE', 'ATENDIDA', 'CERRADA')
       AND v_nuevo IN ('PENDIENTE', 'ATENDIDA', 'CERRADA')
       AND NOT (
           (v_anterior = 'PENDIENTE' AND v_nuevo IN ('PENDIENTE', 'ATENDIDA', 'CERRADA'))
           OR (v_anterior = 'ATENDIDA' AND v_nuevo IN ('ATENDIDA', 'CERRADA'))
           OR (v_anterior = 'CERRADA' AND v_nuevo = 'CERRADA')
       )
    THEN
        RAISE EXCEPTION
            'Transición de alarma no permitida: % -> %',
            v_anterior, v_nuevo
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_transicion_estado_alarma$;

DROP TRIGGER IF EXISTS trg_validar_transicion_estado_alarma
    ON biofloc.alarmas;

CREATE TRIGGER trg_validar_transicion_estado_alarma
BEFORE UPDATE OF estado_alarma_id ON biofloc.alarmas
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_transicion_estado_alarma();


-- Integridad de equipos y respaldo eléctrico.
CREATE OR REPLACE FUNCTION biofloc.validar_catalogos_equipo_activos()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_catalogos_equipo_activos$
DECLARE
    v_tipo_activo BOOLEAN;
    v_estado_activo BOOLEAN;
BEGIN
    SELECT activo INTO v_tipo_activo FROM tipos_equipo WHERE id = NEW.tipo_equipo_id;
    IF v_tipo_activo IS NULL THEN
        RAISE EXCEPTION 'El tipo de equipo % no existe', NEW.tipo_equipo_id USING ERRCODE='foreign_key_violation';
    END IF;
    IF NOT v_tipo_activo THEN
        RAISE EXCEPTION 'El tipo de equipo % está inactivo', NEW.tipo_equipo_id USING ERRCODE='check_violation';
    END IF;

    SELECT activo INTO v_estado_activo FROM estados_equipo WHERE id = NEW.estado_id;
    IF v_estado_activo IS NULL THEN
        RAISE EXCEPTION 'El estado de equipo % no existe', NEW.estado_id USING ERRCODE='foreign_key_violation';
    END IF;
    IF NOT v_estado_activo THEN
        RAISE EXCEPTION 'El estado de equipo % está inactivo', NEW.estado_id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_catalogos_equipo_activos$;

DROP TRIGGER IF EXISTS trg_validar_catalogos_equipo_activos ON biofloc.equipos;
CREATE TRIGGER trg_validar_catalogos_equipo_activos
BEFORE INSERT OR UPDATE OF tipo_equipo_id, estado_id ON biofloc.equipos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_catalogos_equipo_activos();

CREATE OR REPLACE FUNCTION biofloc.validar_equipo_respaldo_operativo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_equipo_respaldo_operativo$
DECLARE
    v_activo BOOLEAN;
    v_estado TEXT;
    v_estado_activo BOOLEAN;
BEGIN
    IF NEW.respaldo_activado AND NEW.equipo_respaldo_id IS NULL THEN
        RAISE EXCEPTION 'equipo_respaldo_id es obligatorio cuando respaldo_activado=true' USING ERRCODE='check_violation';
    END IF;

    IF NEW.respaldo_activado THEN
        SELECT e.activo, ee.nombre, ee.activo
        INTO v_activo, v_estado, v_estado_activo
        FROM biofloc.equipos e
        JOIN biofloc.estados_equipo ee ON ee.id = e.estado_id
        WHERE e.id = NEW.equipo_respaldo_id;

        IF v_activo IS NULL THEN
            RAISE EXCEPTION 'El equipo de respaldo % no existe', NEW.equipo_respaldo_id USING ERRCODE='foreign_key_violation';
        END IF;
        IF NOT v_activo OR NOT v_estado_activo OR v_estado <> 'OPERATIVO' THEN
            RAISE EXCEPTION 'El equipo de respaldo debe estar activo y en estado OPERATIVO' USING ERRCODE='check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_validar_equipo_respaldo_operativo$;

DROP TRIGGER IF EXISTS trg_validar_equipo_respaldo_operativo ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_equipo_respaldo_operativo
BEFORE INSERT OR UPDATE OF respaldo_activado, equipo_respaldo_id ON biofloc.eventos_energia
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_equipo_respaldo_operativo();


-- Coherencia temporal de adquisición de equipos.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_adquisicion_equipo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_fecha_adquisicion_equipo$
DECLARE v_min_fecha DATE;
BEGIN
    IF NEW.fecha_adquisicion IS NULL THEN RETURN NEW; END IF;
    SELECT MIN(fecha) INTO v_min_fecha FROM biofloc.mantenimientos WHERE equipo_id=NEW.id;
    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a un mantenimiento histórico del equipo' USING ERRCODE='check_violation';
    END IF;
    SELECT MIN((fecha_hora AT TIME ZONE 'America/Bogota')::date) INTO v_min_fecha FROM biofloc.fallas WHERE equipo_id=NEW.id;
    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a una falla histórica del equipo' USING ERRCODE='check_violation';
    END IF;
    SELECT MIN((fecha_hora_inicio AT TIME ZONE 'America/Bogota')::date) INTO v_min_fecha FROM biofloc.eventos_energia WHERE equipo_respaldo_id=NEW.id;
    IF v_min_fecha IS NOT NULL AND NEW.fecha_adquisicion > v_min_fecha THEN
        RAISE EXCEPTION 'La fecha de adquisición no puede ser posterior a un evento de energía histórico' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_fecha_adquisicion_equipo$;

DROP TRIGGER IF EXISTS trg_validar_fecha_adquisicion_equipo ON biofloc.equipos;
CREATE TRIGGER trg_validar_fecha_adquisicion_equipo
BEFORE INSERT OR UPDATE OF fecha_adquisicion ON biofloc.equipos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_adquisicion_equipo();

CREATE OR REPLACE FUNCTION biofloc.validar_evento_no_antes_adquisicion_equipo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_evento_no_antes_adquisicion_equipo$
DECLARE v_adquisicion DATE;
BEGIN
    SELECT fecha_adquisicion INTO v_adquisicion FROM biofloc.equipos WHERE id=NEW.equipo_id;
    IF v_adquisicion IS NOT NULL AND (NEW.fecha_hora AT TIME ZONE 'America/Bogota')::date < v_adquisicion THEN
        RAISE EXCEPTION 'La falla no puede ser anterior a la adquisición del equipo' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_evento_no_antes_adquisicion_equipo$;

DROP TRIGGER IF EXISTS trg_validar_falla_no_antes_adquisicion ON biofloc.fallas;
CREATE TRIGGER trg_validar_falla_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_id, fecha_hora ON biofloc.fallas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_antes_adquisicion_equipo();

CREATE OR REPLACE FUNCTION biofloc.validar_mantenimiento_no_antes_adquisicion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_mantenimiento_no_antes_adquisicion$
DECLARE v_adquisicion DATE;
BEGIN
    SELECT fecha_adquisicion INTO v_adquisicion FROM biofloc.equipos WHERE id=NEW.equipo_id;
    IF v_adquisicion IS NOT NULL AND NEW.fecha < v_adquisicion THEN
        RAISE EXCEPTION 'El mantenimiento no puede ser anterior a la adquisición del equipo' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_mantenimiento_no_antes_adquisicion$;

DROP TRIGGER IF EXISTS trg_validar_mantenimiento_no_antes_adquisicion ON biofloc.mantenimientos;
CREATE TRIGGER trg_validar_mantenimiento_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_id, fecha ON biofloc.mantenimientos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_mantenimiento_no_antes_adquisicion();

CREATE OR REPLACE FUNCTION biofloc.validar_respaldo_no_antes_adquisicion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_respaldo_no_antes_adquisicion$
DECLARE v_adquisicion DATE;
BEGIN
    IF NEW.respaldo_activado AND NEW.equipo_respaldo_id IS NOT NULL THEN
        SELECT fecha_adquisicion INTO v_adquisicion FROM biofloc.equipos WHERE id=NEW.equipo_respaldo_id;
        IF v_adquisicion IS NOT NULL AND NEW.fecha_hora_inicio::date < v_adquisicion THEN
            RAISE EXCEPTION 'El evento de energía no puede preceder la adquisición del equipo de respaldo' USING ERRCODE='check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_validar_respaldo_no_antes_adquisicion$;

DROP TRIGGER IF EXISTS trg_validar_respaldo_no_antes_adquisicion ON biofloc.eventos_energia;
CREATE TRIGGER trg_validar_respaldo_no_antes_adquisicion
BEFORE INSERT OR UPDATE OF equipo_respaldo_id, respaldo_activado, fecha_hora_inicio
ON biofloc.eventos_energia
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_respaldo_no_antes_adquisicion();


-- Transición terminal del estado BAJA.
CREATE OR REPLACE FUNCTION biofloc.validar_transicion_estado_equipo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn_validar_transicion_estado_equipo$
DECLARE v_actual TEXT; v_nuevo TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.estado_id = OLD.estado_id THEN RETURN NEW; END IF;
    IF TG_OP = 'UPDATE' THEN
        SELECT nombre INTO v_actual FROM biofloc.estados_equipo WHERE id=OLD.estado_id;
    END IF;
    SELECT nombre INTO v_nuevo FROM biofloc.estados_equipo WHERE id=NEW.estado_id;
    IF TG_OP = 'UPDATE' AND v_actual = 'BAJA' THEN
        RAISE EXCEPTION 'Un equipo en estado BAJA no puede volver a otro estado' USING ERRCODE='check_violation';
    END IF;
    IF v_nuevo = 'BAJA' THEN NEW.activo := FALSE; END IF;
    RETURN NEW;
END;
$fn_validar_transicion_estado_equipo$;

DROP TRIGGER IF EXISTS trg_validar_transicion_estado_equipo ON biofloc.equipos;
CREATE TRIGGER trg_validar_transicion_estado_equipo
BEFORE INSERT OR UPDATE OF estado_id ON biofloc.equipos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_transicion_estado_equipo();


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


COMMIT;



-- Integridad de trazabilidad entre eventos productivos y salidas de inventario.
CREATE OR REPLACE FUNCTION biofloc.validar_trazabilidad_movimiento_automatico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_biofloc_validar_trazabilidad_movimiento_automatico$
DECLARE
    v_tipo VARCHAR(30);
    v_producto BIGINT;
    v_cantidad NUMERIC;
    v_fecha TIMESTAMPTZ;
BEGIN
    IF NEW.referencia_tipo IS NULL OR NEW.referencia_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT nombre INTO v_tipo
      FROM biofloc.tipos_movimiento_inventario
     WHERE id = NEW.tipo_movimiento_id;

    IF NEW.referencia_tipo = 'DETALLE_COMPRA' THEN
        IF v_tipo <> 'ENTRADA' THEN
            RAISE EXCEPTION 'Un detalle de compra solo puede generar un movimiento ENTRADA'
                USING ERRCODE='check_violation';
        END IF;
        SELECT producto_id, cantidad INTO v_producto, v_cantidad
          FROM detalles_compra WHERE id = NEW.referencia_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Detalle de compra % no existe para la trazabilidad', NEW.referencia_id
                USING ERRCODE='foreign_key_violation';
        END IF;
    ELSIF NEW.referencia_tipo = 'ALIMENTACION' THEN
        IF v_tipo <> 'SALIDA' THEN
            RAISE EXCEPTION 'Una alimentación solo puede generar un movimiento SALIDA'
                USING ERRCODE='check_violation';
        END IF;
        SELECT producto_id, cantidad, fecha_hora
          INTO v_producto, v_cantidad, v_fecha
          FROM biofloc.alimentaciones
         WHERE id = NEW.referencia_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Alimentación % no existe para la trazabilidad', NEW.referencia_id
                USING ERRCODE='foreign_key_violation';
        END IF;
    ELSIF NEW.referencia_tipo = 'APLICACION_BIOFLOC' THEN
        IF v_tipo <> 'SALIDA' THEN
            RAISE EXCEPTION 'Una aplicación Biofloc solo puede generar un movimiento SALIDA'
                USING ERRCODE='check_violation';
        END IF;
        SELECT producto_id, cantidad, fecha_hora
          INTO v_producto, v_cantidad, v_fecha
          FROM biofloc.aplicaciones_biofloc
         WHERE id = NEW.referencia_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Aplicación Biofloc % no existe para la trazabilidad', NEW.referencia_id
                USING ERRCODE='foreign_key_violation';
        END IF;
        IF v_producto IS NULL OR v_cantidad IS NULL OR v_cantidad <= 0 THEN
            RAISE EXCEPTION 'La aplicación Biofloc no tiene un consumo de inventario válido'
                USING ERRCODE='check_violation';
        END IF;
    ELSE
        RAISE EXCEPTION 'Referencia de inventario no permitida: %', NEW.referencia_tipo
            USING ERRCODE='check_violation';
    END IF;

    IF NEW.producto_id <> v_producto
       OR NEW.cantidad <> v_cantidad
       OR NEW.fecha_hora <> v_fecha THEN
        RAISE EXCEPTION 'El movimiento no coincide con el evento productivo referenciado'
            USING ERRCODE='check_violation';
    END IF;

    RETURN NEW;
END;
$fn_biofloc_validar_trazabilidad_movimiento_automatico$;


CREATE TRIGGER trg_validar_trazabilidad_movimiento_automatico
BEFORE INSERT OR UPDATE ON movimientos_inventario
FOR EACH ROW
EXECUTE FUNCTION biofloc.validar_trazabilidad_movimiento_automatico();


-- Integridad de secuencia histórica de población.
CREATE OR REPLACE FUNCTION biofloc.validar_secuencia_poblacion_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_biofloc_validar_secuencia_poblacion_historica$
DECLARE
    v_sembrados INTEGER;
    v_max_salidas BIGINT;
BEGIN
    SELECT cantidad_sembrada INTO v_sembrados
      FROM lotes WHERE id = NEW.lote_id FOR UPDATE;

    SELECT COALESCE(MAX(salidas_acumuladas), 0) INTO v_max_salidas
      FROM (
          SELECT fecha_hora,
                 SUM(cantidad_salida) OVER (ORDER BY fecha_hora
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS salidas_acumuladas
          FROM (
              SELECT fecha_hora, cantidad AS cantidad_salida
                FROM mortalidades WHERE lote_id = NEW.lote_id
              UNION ALL
              SELECT fecha_hora, cantidad_peces AS cantidad_salida
                FROM cosechas WHERE lote_id = NEW.lote_id
          ) eventos
      ) secuencia;

    IF v_max_salidas > v_sembrados THEN
        RAISE EXCEPTION 'La secuencia histórica del lote % deja la población negativa', NEW.lote_id
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_biofloc_validar_secuencia_poblacion_historica$;


CREATE CONSTRAINT TRIGGER trg_validar_secuencia_poblacion_mortalidad
AFTER INSERT OR UPDATE ON mortalidades
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_secuencia_poblacion_historica();

CREATE CONSTRAINT TRIGGER trg_validar_secuencia_poblacion_cosecha
AFTER INSERT OR UPDATE ON cosechas
DEFERRABLE INITIALLY IMMEDIATE
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_secuencia_poblacion_historica();


-- Integridad temporal con fecha_cierre de lotes.
CREATE OR REPLACE FUNCTION biofloc.validar_evento_no_despues_cierre()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_evento_no_despues_cierre$
DECLARE
    v_fecha_cierre DATE;
BEGIN
    SELECT fecha_cierre INTO v_fecha_cierre FROM biofloc.lotes WHERE id = NEW.lote_id FOR SHARE;
    IF v_fecha_cierre IS NOT NULL AND (NEW.fecha_hora AT TIME ZONE 'America/Bogota')::date > v_fecha_cierre THEN
        RAISE EXCEPTION 'El evento del lote % no puede ser posterior a su fecha de cierre', NEW.lote_id USING ERRCODE='check_violation';
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
    IF NEW.fecha_cierre IS NULL THEN RETURN NEW; END IF;
    SELECT MAX(fecha_evento) INTO v_ultimo FROM (
        SELECT fecha_hora AS fecha_evento FROM biofloc.biometrias WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.mortalidades WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.cosechas WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.alimentaciones WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.mediciones_biofloc WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.mediciones_agua WHERE lote_id = NEW.id
        UNION ALL SELECT fecha_hora FROM biofloc.aplicaciones_biofloc WHERE lote_id = NEW.id
    ) eventos;
    IF v_ultimo IS NOT NULL AND (v_ultimo AT TIME ZONE 'America/Bogota')::date > NEW.fecha_cierre THEN
        RAISE EXCEPTION 'La fecha de cierre no puede ser anterior al último evento histórico del lote %', NEW.id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_cierre_no_anterior_eventos$;

DROP TRIGGER IF EXISTS trg_validar_cierre_no_anterior_eventos ON biofloc.lotes;
CREATE TRIGGER trg_validar_cierre_no_anterior_eventos BEFORE UPDATE OF fecha_cierre ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_cierre_no_anterior_eventos();

DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_biometrias ON biofloc.biometrias;
CREATE TRIGGER trg_evento_no_despues_cierre_biometrias BEFORE INSERT OR UPDATE ON biofloc.biometrias FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_mortalidades ON biofloc.mortalidades;
CREATE TRIGGER trg_evento_no_despues_cierre_mortalidades BEFORE INSERT OR UPDATE ON biofloc.mortalidades FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_cosechas ON biofloc.cosechas;
CREATE TRIGGER trg_evento_no_despues_cierre_cosechas BEFORE INSERT OR UPDATE ON biofloc.cosechas FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_alimentaciones ON biofloc.alimentaciones;
CREATE TRIGGER trg_evento_no_despues_cierre_alimentaciones BEFORE INSERT OR UPDATE ON biofloc.alimentaciones FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_biofloc ON biofloc.mediciones_biofloc;
CREATE TRIGGER trg_evento_no_despues_cierre_biofloc BEFORE INSERT OR UPDATE ON biofloc.mediciones_biofloc FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_agua ON biofloc.mediciones_agua;
CREATE TRIGGER trg_evento_no_despues_cierre_agua BEFORE INSERT OR UPDATE ON biofloc.mediciones_agua FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();
DROP TRIGGER IF EXISTS trg_evento_no_despues_cierre_aplicaciones ON biofloc.aplicaciones_biofloc;
CREATE TRIGGER trg_evento_no_despues_cierre_aplicaciones BEFORE INSERT OR UPDATE ON biofloc.aplicaciones_biofloc FOR EACH ROW EXECUTE FUNCTION biofloc.validar_evento_no_despues_cierre();


-- Integridad: la fecha de siembra no puede estar en el futuro.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_siembra_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_siembra_no_futura$
BEGIN
    IF NEW.fecha_siembra > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha de siembra no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_siembra_no_futura$;

CREATE TRIGGER trg_validar_fecha_siembra_no_futura
BEFORE INSERT OR UPDATE OF fecha_siembra ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_siembra_no_futura();


-- Integridad: los gastos no pueden estar en el futuro.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_gasto_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_gasto_no_futuro$
BEGIN
    IF NEW.fecha > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha del gasto no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_gasto_no_futuro$;

CREATE TRIGGER trg_validar_fecha_gasto_no_futura
BEFORE INSERT OR UPDATE ON biofloc.gastos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_gasto_no_futura();


-- Integridad temporal: compras, ventas y movimientos de inventario no pueden ser futuros.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_comercial_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_comercial_no_futura$
BEGIN
    IF NEW.fecha > (NOW() AT TIME ZONE 'America/Bogota')::date THEN
        RAISE EXCEPTION 'La fecha comercial no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_fecha_comercial_no_futura$;

CREATE OR REPLACE FUNCTION biofloc.validar_fecha_movimiento_no_futura()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_movimiento_no_futura$
BEGIN
    IF NEW.fecha_hora > NOW() THEN
        RAISE EXCEPTION 'La fecha/hora del movimiento de inventario no puede estar en el futuro' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_fecha_movimiento_no_futura$;

CREATE TRIGGER trg_validar_fecha_compra_no_futura
BEFORE INSERT OR UPDATE ON biofloc.compras
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_comercial_no_futura();
CREATE TRIGGER trg_validar_fecha_venta_no_futura
BEFORE INSERT OR UPDATE ON biofloc.ventas
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_comercial_no_futura();
CREATE TRIGGER trg_validar_fecha_movimiento_no_futura
BEFORE INSERT OR UPDATE ON biofloc.movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_movimiento_no_futura();


-- Integridad: las unidades/factor de un producto quedan inmutables tras su primer movimiento.
CREATE OR REPLACE FUNCTION biofloc.validar_unidad_producto_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_unidad_producto_historica$
BEGIN
    IF (NEW.unidad_id IS DISTINCT FROM OLD.unidad_id
        OR NEW.unidad_comercial_id IS DISTINCT FROM OLD.unidad_comercial_id
        OR NEW.factor_conversion IS DISTINCT FROM OLD.factor_conversion)
       AND EXISTS (SELECT 1 FROM biofloc.movimientos_inventario WHERE producto_id = OLD.id)
    THEN
        RAISE EXCEPTION 'No se pueden cambiar las unidades o el factor de conversión de un producto con movimientos históricos'
            USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_unidad_producto_historica$;

CREATE TRIGGER trg_validar_unidad_producto_historica
BEFORE UPDATE OF unidad_id, unidad_comercial_id, factor_conversion ON biofloc.productos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_unidad_producto_historica();


-- Integridad: registros históricos ligados a inventario son inmutables.
CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_impedir_modificacion_historico$
BEGIN
    RAISE EXCEPTION 'El registro histórico % de la tabla % es inmutable', OLD.id, TG_TABLE_NAME USING ERRCODE='check_violation';
END;
$fn_impedir_modificacion_historico$;

CREATE TRIGGER trg_inmutabilidad_movimientos_inventario
BEFORE UPDATE OR DELETE ON biofloc.movimientos_inventario
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();
CREATE TRIGGER trg_inmutabilidad_alimentaciones
BEFORE UPDATE OR DELETE ON biofloc.alimentaciones
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();
CREATE TRIGGER trg_inmutabilidad_aplicaciones_biofloc
BEFORE UPDATE OR DELETE ON biofloc.aplicaciones_biofloc
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();
CREATE TRIGGER trg_inmutabilidad_detalles_compra
BEFORE UPDATE OR DELETE ON biofloc.detalles_compra
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_historico();


-- Integridad: ventas y detalles comerciales son históricos e inmutables.
CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_venta_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_inmutabilidad_venta$
BEGIN
    RAISE EXCEPTION 'La venta histórica % es inmutable; registre una corrección mediante un nuevo documento', OLD.id USING ERRCODE='check_violation';
END;
$fn_inmutabilidad_venta$;

CREATE TRIGGER trg_inmutabilidad_ventas
BEFORE UPDATE OR DELETE ON ventas
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_venta_historica();

CREATE TRIGGER trg_inmutabilidad_detalles_venta
BEFORE UPDATE OR DELETE ON detalles_venta
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_venta_historica();


-- Integridad: compras y gastos históricos son inmutables.
CREATE OR REPLACE FUNCTION biofloc.impedir_modificacion_financiera_historica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_inmutabilidad_financiera$
BEGIN
    RAISE EXCEPTION 'El registro financiero histórico % de la tabla % es inmutable', OLD.id, TG_TABLE_NAME USING ERRCODE='check_violation';
END;
$fn_inmutabilidad_financiera$;

CREATE TRIGGER trg_inmutabilidad_compras
BEFORE UPDATE OR DELETE ON compras
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_financiera_historica();

CREATE TRIGGER trg_inmutabilidad_gastos
BEFORE UPDATE OR DELETE ON gastos
FOR EACH ROW EXECUTE FUNCTION biofloc.impedir_modificacion_financiera_historica();


-- Integridad temporal: gasto directo de lote no puede preceder la siembra.
CREATE OR REPLACE FUNCTION biofloc.validar_fecha_gasto_lote()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_fecha_gasto_lote$
DECLARE
    v_fecha_siembra DATE;
BEGIN
    IF NEW.lote_id IS NULL THEN RETURN NEW; END IF;
    SELECT l.fecha_siembra INTO v_fecha_siembra FROM biofloc.lotes l WHERE l.id = NEW.lote_id;
    IF v_fecha_siembra IS NULL THEN
        RAISE EXCEPTION 'No existe el lote %', NEW.lote_id USING ERRCODE='foreign_key_violation';
    END IF;
    IF NEW.fecha < v_fecha_siembra THEN
        RAISE EXCEPTION 'La fecha del gasto % no puede ser anterior a la siembra del lote %', NEW.fecha, NEW.lote_id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_fecha_gasto_lote$;

DROP TRIGGER IF EXISTS trg_validar_fecha_gasto_lote ON biofloc.gastos;
CREATE TRIGGER trg_validar_fecha_gasto_lote
BEFORE INSERT OR UPDATE OF fecha, lote_id ON biofloc.gastos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_fecha_gasto_lote();


    
-- Integridad histórica del catálogo de tipos de mantenimiento.
CREATE OR REPLACE FUNCTION biofloc.validar_tipo_mantenimiento_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_tipo_mantenimiento_historico$
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (
           SELECT 1 FROM biofloc.mantenimientos
           WHERE tipo_mantenimiento_id = OLD.id
       )
    THEN
        RAISE EXCEPTION
            'El tipo de mantenimiento % ya tiene registros históricos y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_OP = 'INSERT' OR NEW.tipo_mantenimiento_id IS DISTINCT FROM OLD.tipo_mantenimiento_id THEN
        IF NOT EXISTS (
            SELECT 1 FROM biofloc.tipos_mantenimiento
            WHERE id = NEW.tipo_mantenimiento_id AND activo = TRUE
        ) THEN
            RAISE EXCEPTION
                'El tipo de mantenimiento % debe existir y estar activo',
                NEW.tipo_mantenimiento_id USING ERRCODE='check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_validar_tipo_mantenimiento_historico$;

DROP TRIGGER IF EXISTS trg_validar_tipo_mantenimiento_historico ON biofloc.tipos_mantenimiento;
CREATE TRIGGER trg_validar_tipo_mantenimiento_historico
BEFORE UPDATE OF nombre ON biofloc.tipos_mantenimiento
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_tipo_mantenimiento_historico();

DROP TRIGGER IF EXISTS trg_validar_tipo_mantenimiento_activo ON biofloc.mantenimientos;
CREATE TRIGGER trg_validar_tipo_mantenimiento_activo
BEFORE INSERT OR UPDATE OF tipo_mantenimiento_id ON biofloc.mantenimientos
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_tipo_mantenimiento_historico();

    
-- Los nombres de catálogos de equipos son parte de su semántica operativa.
CREATE OR REPLACE FUNCTION biofloc.validar_catalogo_equipo_historico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_catalogo_equipo_historico$
BEGIN
    IF TG_TABLE_NAME = 'tipos_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (SELECT 1 FROM biofloc.equipos WHERE tipo_equipo_id = OLD.id)
    THEN
        RAISE EXCEPTION 'El tipo de equipo % ya está referenciado y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'estados_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND EXISTS (SELECT 1 FROM biofloc.equipos WHERE estado_id = OLD.id)
    THEN
        RAISE EXCEPTION 'El estado de equipo % ya está referenciado y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'estados_equipo'
       AND NEW.nombre IS DISTINCT FROM OLD.nombre
       AND OLD.nombre IN ('OPERATIVO', 'BAJA', 'FUERA_DE_SERVICIO')
    THEN
        RAISE EXCEPTION 'El estado de equipo % es reservado por las reglas operativas y no puede renombrarse',
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
        RAISE EXCEPTION 'El parámetro de agua % ya tiene historial/referencias y no puede renombrarse',
            OLD.id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'referencias_agua'
       AND (TG_OP = 'INSERT' OR NEW.parametro_id IS DISTINCT FROM OLD.parametro_id)
       AND NOT EXISTS (
           SELECT 1 FROM biofloc.parametros_agua WHERE id = NEW.parametro_id AND activo = TRUE
       )
    THEN
        RAISE EXCEPTION 'El parámetro de agua % debe existir y estar activo',
            NEW.parametro_id USING ERRCODE='check_violation';
    END IF;

    IF TG_TABLE_NAME = 'aplicaciones_biofloc'
       AND (TG_OP = 'INSERT' OR NEW.tipo_aplicacion_id IS DISTINCT FROM OLD.tipo_aplicacion_id)
       AND NOT EXISTS (
           SELECT 1 FROM biofloc.tipos_aplicacion_biofloc
           WHERE id = NEW.tipo_aplicacion_id AND activo = TRUE
       )
    THEN
        RAISE EXCEPTION 'El tipo de aplicación Biofloc % debe existir y estar activo',
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

    
-- Catálogos de especie y etapa: sus nombres son parte de la interpretación histórica.
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
       AND (TG_OP = 'INSERT'
            OR NEW.especie_id IS DISTINCT FROM OLD.especie_id
            OR NEW.etapa_productiva_id IS DISTINCT FROM OLD.etapa_productiva_id)
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
    IF NOT FOUND OR NOT activo_catalogo THEN RAISE EXCEPTION 'El estado de lote debe existir y estar activo' USING ERRCODE='check_violation'; END IF;
    SELECT nombre INTO nombre_anterior FROM biofloc.estados_lote WHERE id = OLD.estado_id;
    IF nombre_anterior IN ('FINALIZADO', 'CANCELADO') AND nombre_nuevo <> nombre_anterior THEN RAISE EXCEPTION 'Un lote % no puede reabrirse ni cambiar de estado', nombre_anterior USING ERRCODE='check_violation'; END IF;
    IF nombre_nuevo IN ('FINALIZADO', 'CANCELADO') AND NEW.fecha_cierre IS NULL THEN RAISE EXCEPTION 'El estado % requiere fecha_cierre', nombre_nuevo USING ERRCODE='check_violation'; END IF;
    IF nombre_nuevo = 'ACTIVO' AND NEW.fecha_cierre IS NOT NULL THEN RAISE EXCEPTION 'Un lote ACTIVO no puede tener fecha_cierre' USING ERRCODE='check_violation'; END IF;
    RETURN NEW;
END;
$fn_validar_estado_lote_operativo$;
DROP TRIGGER IF EXISTS trg_validar_estado_lote_operativo ON biofloc.lotes;
CREATE TRIGGER trg_validar_estado_lote_operativo BEFORE INSERT OR UPDATE OF estado_id, fecha_cierre ON biofloc.lotes FOR EACH ROW EXECUTE FUNCTION biofloc.validar_estado_lote_operativo();

CREATE OR REPLACE FUNCTION biofloc.validar_estado_estanque_operativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_estado_estanque_operativo$
DECLARE nombre_nuevo TEXT; activo_catalogo BOOLEAN;
BEGIN
    PERFORM pg_advisory_xact_lock(2147483000, NEW.id);
    SELECT nombre, activo INTO nombre_nuevo, activo_catalogo FROM biofloc.estados_estanque WHERE id = NEW.estado_id;
    IF NOT FOUND OR NOT activo_catalogo THEN RAISE EXCEPTION 'El estado de estanque debe existir y estar activo' USING ERRCODE='check_violation'; END IF;
    IF NEW.activo = FALSE AND EXISTS (SELECT 1 FROM biofloc.lotes l JOIN biofloc.estados_lote el ON el.id=l.estado_id WHERE l.estanque_id=NEW.id AND el.nombre='ACTIVO') THEN RAISE EXCEPTION 'No se puede desactivar un estanque con un lote ACTIVO' USING ERRCODE='check_violation'; END IF;
    IF EXISTS (SELECT 1 FROM biofloc.lotes l JOIN biofloc.estados_lote el ON el.id=l.estado_id WHERE l.estanque_id=NEW.id AND el.nombre='ACTIVO')
       AND nombre_nuevo <> 'OCUPADO'
    THEN
        RAISE EXCEPTION 'Un estanque con lote ACTIVO debe permanecer en estado OCUPADO' USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_estado_estanque_operativo$;
DROP TRIGGER IF EXISTS trg_validar_estado_estanque_operativo ON biofloc.estanques;
CREATE TRIGGER trg_validar_estado_estanque_operativo BEFORE INSERT OR UPDATE OF estado_id, activo ON biofloc.estanques FOR EACH ROW EXECUTE FUNCTION biofloc.validar_estado_estanque_operativo();

    
CREATE OR REPLACE FUNCTION biofloc.proteger_catalogos_estados_operativos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_proteger_catalogos_estados_operativos$
BEGIN
    IF TG_TABLE_NAME = 'estados_lote' AND NEW.nombre IS DISTINCT FROM OLD.nombre THEN
        IF OLD.nombre IN ('PLANIFICADO', 'ACTIVO', 'FINALIZADO', 'CANCELADO')
           OR EXISTS (SELECT 1 FROM biofloc.lotes WHERE estado_id = OLD.id)
        THEN RAISE EXCEPTION 'El estado de lote % es semántico o tiene historial y no puede renombrarse', OLD.nombre USING ERRCODE='check_violation'; END IF;
    END IF;
    IF TG_TABLE_NAME = 'estados_estanque' AND NEW.nombre IS DISTINCT FROM OLD.nombre THEN
        IF OLD.nombre IN ('DISPONIBLE', 'OCUPADO', 'MANTENIMIENTO', 'FUERA_DE_SERVICIO')
           OR EXISTS (SELECT 1 FROM biofloc.estanques WHERE estado_id = OLD.id)
        THEN RAISE EXCEPTION 'El estado de estanque % es semántico o tiene historial y no puede renombrarse', OLD.nombre USING ERRCODE='check_violation'; END IF;
    END IF;
    IF TG_TABLE_NAME = 'estados_lote' AND NEW.activo IS DISTINCT FROM OLD.activo AND NEW.activo = FALSE
       AND EXISTS (SELECT 1 FROM biofloc.lotes l WHERE l.estado_id = OLD.id AND l.fecha_cierre IS NULL)
    THEN RAISE EXCEPTION 'No se puede desactivar un estado de lote utilizado por lotes sin cierre' USING ERRCODE='check_violation'; END IF;
    IF TG_TABLE_NAME = 'estados_estanque' AND NEW.activo IS DISTINCT FROM OLD.activo AND NEW.activo = FALSE
       AND EXISTS (SELECT 1 FROM biofloc.estanques e WHERE e.estado_id = OLD.id AND e.activo = TRUE)
    THEN RAISE EXCEPTION 'No se puede desactivar un estado de estanque utilizado por estanques activos' USING ERRCODE='check_violation'; END IF;
    RETURN NEW;
END;
$fn_proteger_catalogos_estados_operativos$;
DROP TRIGGER IF EXISTS trg_proteger_catalogos_estados_lote ON biofloc.estados_lote;
CREATE TRIGGER trg_proteger_catalogos_estados_lote BEFORE UPDATE OF nombre, activo ON biofloc.estados_lote FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_catalogos_estados_operativos();
DROP TRIGGER IF EXISTS trg_proteger_catalogos_estados_estanque ON biofloc.estados_estanque;
CREATE TRIGGER trg_proteger_catalogos_estados_estanque BEFORE UPDATE OF nombre, activo ON biofloc.estados_estanque FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_catalogos_estados_operativos();


-- Un lote ACTIVO solo puede ocupar un estanque operativo.
-- Comparte el mismo bloqueo transaccional por estanque con la validación de
-- estado del estanque para evitar carreras entre ambas operaciones.
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


-- Protección de stock histórico: no se permite que una inserción deje
-- existencias negativas en ningún punto de la línea temporal.
CREATE OR REPLACE FUNCTION biofloc.validar_stock_historico_no_negativo()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_stock_historico_no_negativo$
DECLARE
    v_stock NUMERIC := 0;
    v_row RECORD;
BEGIN
    PERFORM pg_advisory_xact_lock(2147482000, NEW.producto_id);
    FOR v_row IN
        SELECT mi.cantidad,
               CASE WHEN tm.nombre = 'AJUSTE' THEN mi.efecto_stock ELSE tm.afecta_stock END AS efecto
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.tipos_movimiento_inventario tm ON tm.id = mi.tipo_movimiento_id
        WHERE mi.producto_id = NEW.producto_id
        ORDER BY mi.fecha_hora ASC, mi.id ASC
    LOOP
        v_stock := v_stock + (v_row.cantidad * v_row.efecto);
        IF v_stock < 0 THEN
            RAISE EXCEPTION 'El movimiento del producto % dejaría stock negativo en algún punto de su historia',
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


-- Datos fundacionales del lote: inmutables una vez iniciado/cerrado el historial.
CREATE OR REPLACE FUNCTION biofloc.proteger_datos_fundacionales_lote()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_proteger_datos_fundacionales_lote$
DECLARE
    v_tiene_historial BOOLEAN;
BEGIN
    SELECT (
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
    ) INTO v_tiene_historial;

    IF v_tiene_historial AND (
        NEW.estanque_id IS DISTINCT FROM OLD.estanque_id
        OR NEW.especie_id IS DISTINCT FROM OLD.especie_id
        OR NEW.etapa_productiva_id IS DISTINCT FROM OLD.etapa_productiva_id
        OR NEW.cantidad_sembrada IS DISTINCT FROM OLD.cantidad_sembrada
        OR NEW.peso_inicial_promedio_g IS DISTINCT FROM OLD.peso_inicial_promedio_g
    ) THEN
        RAISE EXCEPTION
            'Los datos fundacionales del lote % son inmutables una vez iniciado o cerrado su historial',
            OLD.id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_proteger_datos_fundacionales_lote$;

DROP TRIGGER IF EXISTS trg_proteger_datos_fundacionales_lote ON biofloc.lotes;
CREATE TRIGGER trg_proteger_datos_fundacionales_lote
BEFORE UPDATE OF estanque_id, especie_id, etapa_productiva_id, cantidad_sembrada, peso_inicial_promedio_g
ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.proteger_datos_fundacionales_lote();


-- Un estanque no puede alojar ciclos productivos con periodos superpuestos.
CREATE OR REPLACE FUNCTION biofloc.validar_solapamiento_historico_estanque()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_solapamiento_historico_estanque$
BEGIN
    PERFORM pg_advisory_xact_lock(2147483000, NEW.estanque_id);
    IF EXISTS (
        SELECT 1 FROM biofloc.lotes l
        WHERE l.estanque_id = NEW.estanque_id
          AND l.id <> NEW.id
          AND l.fecha_siembra <= COALESCE(NEW.fecha_cierre, DATE '9999-12-31')
          AND COALESCE(l.fecha_cierre, DATE '9999-12-31') >= NEW.fecha_siembra
    ) THEN
        RAISE EXCEPTION
            'El estanque % ya tiene un ciclo histórico que se solapa con el periodo del lote',
            NEW.estanque_id USING ERRCODE='exclusion_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_solapamiento_historico_estanque$;

DROP TRIGGER IF EXISTS trg_validar_solapamiento_historico_estanque ON biofloc.lotes;
CREATE TRIGGER trg_validar_solapamiento_historico_estanque
BEFORE INSERT OR UPDATE OF estanque_id, fecha_siembra, fecha_cierre
ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_solapamiento_historico_estanque();


-- Si una mortalidad lleva la población AS-OF a cero, finaliza el lote.
CREATE OR REPLACE FUNCTION biofloc.finalizar_lote_por_mortalidad_total()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_finalizar_lote_por_mortalidad_total$
DECLARE
    v_sembrados INTEGER;
    v_mortalidad INTEGER;
    v_cosecha INTEGER;
    v_estado_final BIGINT;
BEGIN
    SELECT cantidad_sembrada INTO v_sembrados FROM biofloc.lotes WHERE id = NEW.lote_id FOR UPDATE;
    SELECT COALESCE(SUM(cantidad), 0) INTO v_mortalidad
    FROM biofloc.mortalidades WHERE lote_id = NEW.lote_id AND fecha_hora <= NEW.fecha_hora;
    SELECT COALESCE(SUM(cantidad_peces), 0) INTO v_cosecha
    FROM biofloc.cosechas WHERE lote_id = NEW.lote_id AND fecha_hora <= NEW.fecha_hora;

    IF v_sembrados - v_mortalidad - v_cosecha = 0 THEN
        SELECT id INTO v_estado_final FROM biofloc.estados_lote WHERE nombre = 'FINALIZADO';
        IF v_estado_final IS NOT NULL THEN
            UPDATE biofloc.lotes
            SET estado_id = v_estado_final,
                fecha_cierre = COALESCE(fecha_cierre, (NEW.fecha_hora AT TIME ZONE 'America/Bogota')::date)
            WHERE id = NEW.lote_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_finalizar_lote_por_mortalidad_total$;

DROP TRIGGER IF EXISTS trg_finalizar_lote_por_mortalidad_total ON biofloc.mortalidades;
CREATE TRIGGER trg_finalizar_lote_por_mortalidad_total
AFTER INSERT ON biofloc.mortalidades
FOR EACH ROW EXECUTE FUNCTION biofloc.finalizar_lote_por_mortalidad_total();


-- FINALIZADO representa un ciclo agotado: exige población cero.
CREATE OR REPLACE FUNCTION biofloc.validar_lote_finalizado_sin_peces()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_lote_finalizado_sin_peces$
DECLARE
    v_estado TEXT;
    v_poblacion INTEGER;
BEGIN
    SELECT nombre INTO v_estado FROM biofloc.estados_lote WHERE id = NEW.estado_id;
    IF v_estado = 'FINALIZADO' THEN
        SELECT NEW.cantidad_sembrada
             - COALESCE((SELECT SUM(cantidad) FROM biofloc.mortalidades WHERE lote_id = NEW.id), 0)
             - COALESCE((SELECT SUM(cantidad_peces) FROM biofloc.cosechas WHERE lote_id = NEW.id), 0)
        INTO v_poblacion;
        IF v_poblacion <> 0 THEN
            RAISE EXCEPTION 'Un lote FINALIZADO debe tener población cero; población disponible: %',
                v_poblacion USING ERRCODE='check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn_validar_lote_finalizado_sin_peces$;

DROP TRIGGER IF EXISTS trg_validar_lote_finalizado_sin_peces ON biofloc.lotes;
CREATE TRIGGER trg_validar_lote_finalizado_sin_peces
BEFORE INSERT OR UPDATE OF estado_id, cantidad_sembrada
ON biofloc.lotes
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_lote_finalizado_sin_peces();

CREATE OR REPLACE FUNCTION biofloc.validar_venta_dentro_ciclo_lote()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_venta_dentro_ciclo_lote$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM biofloc.detalles_venta d
        JOIN biofloc.lotes l ON l.id = d.lote_id
        WHERE d.venta_id = NEW.id
          AND (
              NEW.fecha < l.fecha_siembra
              OR (l.fecha_cierre IS NOT NULL AND NEW.fecha > l.fecha_cierre)
          )
    ) THEN
        RAISE EXCEPTION 'La venta % está fuera del intervalo del lote asociado', NEW.id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_venta_dentro_ciclo_lote$;

DROP TRIGGER IF EXISTS trg_validar_venta_dentro_ciclo_lote ON biofloc.ventas;
CREATE CONSTRAINT TRIGGER trg_validar_venta_dentro_ciclo_lote
AFTER INSERT OR UPDATE OF fecha ON biofloc.ventas
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_venta_dentro_ciclo_lote();

CREATE OR REPLACE FUNCTION biofloc.validar_detalle_venta_dentro_ciclo_lote()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_detalle_venta_dentro_ciclo_lote$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM biofloc.ventas v
        JOIN biofloc.lotes l ON l.id = NEW.lote_id
        WHERE v.id = NEW.venta_id
          AND (
              v.fecha < l.fecha_siembra
              OR (l.fecha_cierre IS NOT NULL AND v.fecha > l.fecha_cierre)
          )
    ) THEN
        RAISE EXCEPTION 'El detalle de venta % está fuera del intervalo del lote asociado', NEW.id USING ERRCODE='check_violation';
    END IF;
    RETURN NEW;
END;
$fn_validar_detalle_venta_dentro_ciclo_lote$;

DROP TRIGGER IF EXISTS trg_validar_detalle_venta_dentro_ciclo_lote ON biofloc.detalles_venta;
CREATE CONSTRAINT TRIGGER trg_validar_detalle_venta_dentro_ciclo_lote
AFTER INSERT OR UPDATE OF venta_id, lote_id ON biofloc.detalles_venta
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_detalle_venta_dentro_ciclo_lote();



-- Protege la secuencia histórica de ventas frente a inserciones retroactivas.
CREATE OR REPLACE FUNCTION biofloc.validar_secuencia_historica_ventas()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn_validar_secuencia_historica_ventas$
DECLARE
    v_lote_id BIGINT;
    v_fecha DATE;
    v_cosechado NUMERIC;
    v_vendido NUMERIC;
BEGIN
    FOR v_lote_id IN
        SELECT DISTINCT d.lote_id FROM biofloc.detalles_venta d WHERE d.venta_id = NEW.id
    LOOP
        PERFORM pg_advisory_xact_lock(2147481000, v_lote_id);
        FOR v_fecha, v_cosechado, v_vendido IN
            WITH cosechas AS (
                SELECT (c.fecha_hora AT TIME ZONE 'America/Bogota')::date AS fecha, SUM(c.peso_total_kg) AS kg
                FROM biofloc.cosechas c WHERE c.lote_id = v_lote_id GROUP BY 1
            ),
            ventas AS (
                SELECT v.fecha, SUM(d.cantidad) AS kg
                FROM biofloc.ventas v
                JOIN biofloc.detalles_venta d ON d.venta_id = v.id
                WHERE d.lote_id = v_lote_id GROUP BY v.fecha
            ),
            fechas AS (SELECT fecha FROM cosechas UNION SELECT fecha FROM ventas)
            SELECT f.fecha,
                   COALESCE((SELECT SUM(c.kg) FROM cosechas c WHERE c.fecha <= f.fecha), 0),
                   COALESCE((SELECT SUM(v.kg) FROM ventas v WHERE v.fecha <= f.fecha), 0)
            FROM fechas f ORDER BY f.fecha
        LOOP
            IF v_vendido > v_cosechado THEN
                RAISE EXCEPTION 'La secuencia histórica de ventas del lote % supera la biomasa cosechada al %',
                    v_lote_id, v_fecha USING ERRCODE='check_violation';
            END IF;
        END LOOP;
    END LOOP;
    RETURN NEW;
END;
$fn_validar_secuencia_historica_ventas$;

DROP TRIGGER IF EXISTS trg_validar_secuencia_historica_ventas ON biofloc.ventas;
CREATE CONSTRAINT TRIGGER trg_validar_secuencia_historica_ventas
AFTER INSERT ON biofloc.ventas
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION biofloc.validar_secuencia_historica_ventas();

