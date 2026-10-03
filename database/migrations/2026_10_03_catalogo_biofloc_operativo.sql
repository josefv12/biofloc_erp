-- Catálogo Biofloc operativo: 4 insumos + referencias semanales para Tilapia roja.
-- Las cantidades son una referencia presupuestal basada en 1.100 peces y el ciclo
-- de 400 kg del presupuesto aprobado. No son una dosis científica universal.
-- Ajustar en operación con TAN, nitrito, alcalinidad, pH, sólidos y ficha técnica.
SET search_path TO biofloc, public;

BEGIN;

INSERT INTO categorias_inventario (nombre, descripcion)
VALUES
  ('FUENTE_CARBONO', 'Fuentes de carbono para Biofloc'),
  ('PROBIOTICO', 'Productos probióticos para Biofloc'),
  ('CORRECTIVO', 'Correctivos utilizados en el sistema Biofloc')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO unidades (nombre, simbolo)
VALUES ('Kilogramo', 'kg')
ON CONFLICT (simbolo) DO NOTHING;

ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS unidad_comercial_id BIGINT,
  ADD COLUMN IF NOT EXISTS factor_conversion NUMERIC(18,6) NOT NULL DEFAULT 1;

UPDATE productos
SET unidad_comercial_id = unidad_id
WHERE unidad_comercial_id IS NULL;

ALTER TABLE productos
  ALTER COLUMN unidad_comercial_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fk_productos_unidad_comercial'
      AND conrelid = 'biofloc.productos'::regclass
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT fk_productos_unidad_comercial
      FOREIGN KEY (unidad_comercial_id) REFERENCES unidades(id);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'productos_factor_conversion_check'
      AND conrelid = 'biofloc.productos'::regclass
  ) THEN
    ALTER TABLE productos
      ADD CONSTRAINT productos_factor_conversion_check
      CHECK (factor_conversion > 0);
  END IF;
END $$;

-- Productos Biofloc: se crean en catálogo con stock inicial 0.
INSERT INTO productos (
  codigo, nombre, categoria_id, unidad_id, unidad_comercial_id,
  factor_conversion, stock_minimo, activo
)
SELECT
  v.codigo,
  v.nombre,
  c.id,
  u.id,
  u.id,
  1,
  0,
  TRUE
FROM (
  VALUES
    ('BF-MELAZA', 'Melaza de caña', 'FUENTE_CARBONO'),
    ('BF-PROBIOTICO', 'Probiótico Biofloc', 'PROBIOTICO'),
    ('BF-BICARBONATO', 'Bicarbonato de sodio', 'CORRECTIVO'),
    ('BF-SAL-MARINA', 'Sal marina', 'CORRECTIVO')
) AS v(codigo, nombre, categoria)
JOIN categorias_inventario c ON c.nombre = v.categoria
JOIN unidades u ON u.simbolo = 'kg'
ON CONFLICT (codigo) DO UPDATE
SET nombre = EXCLUDED.nombre,
    categoria_id = EXCLUDED.categoria_id,
    unidad_id = EXCLUDED.unidad_id,
    unidad_comercial_id = EXCLUDED.unidad_comercial_id,
    factor_conversion = EXCLUDED.factor_conversion,
    activo = TRUE;

CREATE TABLE IF NOT EXISTS referencias_aplicacion_biofloc (
  id BIGSERIAL PRIMARY KEY,
  especie_id BIGINT NOT NULL REFERENCES especies(id),
  semana INTEGER NOT NULL CHECK (semana > 0),
  fase VARCHAR(40) NOT NULL CHECK (fase IN ('Inicio', 'Levante', 'Engorde')),
  producto_id BIGINT NOT NULL REFERENCES productos(id),
  cantidad_referencia NUMERIC(12,4) NOT NULL CHECK (cantidad_referencia >= 0),
  unidad VARCHAR(20) NOT NULL DEFAULT 'kg',
  base_peces INTEGER NOT NULL DEFAULT 1100 CHECK (base_peces > 0),
  biomasa_objetivo_kg NUMERIC(12,4),
  observaciones TEXT,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (especie_id, semana, producto_id)
);

CREATE INDEX IF NOT EXISTS idx_ref_aplicacion_biofloc_especie_semana
  ON referencias_aplicacion_biofloc (especie_id, semana);

-- Ciclo de referencia del presupuesto: 1.100 peces, objetivo 400 kg.
-- Semanas 1-4 Inicio, 5-10 Levante, 11-20 Engorde.
INSERT INTO referencias_aplicacion_biofloc (
  especie_id, semana, fase, producto_id, cantidad_referencia, unidad,
  base_peces, biomasa_objetivo_kg, observaciones, activo
)
SELECT
  e.id,
  v.semana,
  v.fase,
  p.id,
  v.cantidad,
  'kg',
  1100,
  v.biomasa,
  'Referencia presupuestal del ciclo 1.100 peces / 400 kg. Ajustar según TAN, alcalinidad, pH, sólidos, salinidad/cloruros y ficha técnica del producto.',
  TRUE
FROM especies e
JOIN productos p ON p.codigo = v.codigo
CROSS JOIN (
  VALUES
    (1,'Inicio','BF-MELAZA',6.1969,6.00875),
    (1,'Inicio','BF-BICARBONATO',1.2195,6.00875),
    (1,'Inicio','BF-PROBIOTICO',0.0500,6.00875),
    (1,'Inicio','BF-SAL-MARINA',0.0000,6.00875),
    (2,'Inicio','BF-MELAZA',6.1969,10.9725),
    (2,'Inicio','BF-BICARBONATO',1.2195,10.9725),
    (2,'Inicio','BF-PROBIOTICO',0.0500,10.9725),
    (2,'Inicio','BF-SAL-MARINA',0.0000,10.9725),
    (3,'Inicio','BF-MELAZA',6.1969,15.93625),
    (3,'Inicio','BF-BICARBONATO',1.2195,15.93625),
    (3,'Inicio','BF-PROBIOTICO',0.0500,15.93625),
    (3,'Inicio','BF-SAL-MARINA',0.0000,15.93625),
    (4,'Inicio','BF-MELAZA',6.1969,20.9),
    (4,'Inicio','BF-BICARBONATO',1.2195,20.9),
    (4,'Inicio','BF-PROBIOTICO',0.0500,20.9),
    (4,'Inicio','BF-SAL-MARINA',5.5280,20.9),
    (5,'Levante','BF-MELAZA',11.4154,30.04375),
    (5,'Levante','BF-BICARBONATO',2.2464,30.04375),
    (5,'Levante','BF-PROBIOTICO',0.0500,30.04375),
    (5,'Levante','BF-SAL-MARINA',0.0000,30.04375),
    (6,'Levante','BF-MELAZA',11.4154,39.1875),
    (6,'Levante','BF-BICARBONATO',2.2464,39.1875),
    (6,'Levante','BF-PROBIOTICO',0.0500,39.1875),
    (6,'Levante','BF-SAL-MARINA',0.0000,39.1875),
    (7,'Levante','BF-MELAZA',11.4154,48.33125),
    (7,'Levante','BF-BICARBONATO',2.2464,48.33125),
    (7,'Levante','BF-PROBIOTICO',0.0500,48.33125),
    (7,'Levante','BF-SAL-MARINA',0.0000,48.33125),
    (8,'Levante','BF-MELAZA',11.4154,57.475),
    (8,'Levante','BF-BICARBONATO',2.2464,57.475),
    (8,'Levante','BF-PROBIOTICO',0.0500,57.475),
    (8,'Levante','BF-SAL-MARINA',5.5280,57.475),
    (9,'Levante','BF-MELAZA',21.2,74.45625),
    (9,'Levante','BF-BICARBONATO',4.1719,74.45625),
    (9,'Levante','BF-PROBIOTICO',0.0500,74.45625),
    (9,'Levante','BF-SAL-MARINA',0.0000,74.45625),
    (10,'Levante','BF-MELAZA',21.2,91.4375),
    (10,'Levante','BF-BICARBONATO',4.1719,91.4375),
    (10,'Levante','BF-PROBIOTICO',0.0500,91.4375),
    (10,'Levante','BF-SAL-MARINA',0.0000,91.4375),
    (11,'Engorde','BF-MELAZA',21.2,108.41875),
    (11,'Engorde','BF-BICARBONATO',4.1719,108.41875),
    (11,'Engorde','BF-PROBIOTICO',0.0500,108.41875),
    (11,'Engorde','BF-SAL-MARINA',0.0000,108.41875),
    (12,'Engorde','BF-MELAZA',21.2,125.4),
    (12,'Engorde','BF-BICARBONATO',4.1719,125.4),
    (12,'Engorde','BF-PROBIOTICO',0.0500,125.4),
    (12,'Engorde','BF-SAL-MARINA',5.5280,125.4),
    (13,'Engorde','BF-MELAZA',42.3999,159.3625),
    (13,'Engorde','BF-BICARBONATO',8.3438,159.3625),
    (13,'Engorde','BF-PROBIOTICO',0.0500,159.3625),
    (13,'Engorde','BF-SAL-MARINA',0.0000,159.3625),
    (14,'Engorde','BF-MELAZA',42.3999,193.325),
    (14,'Engorde','BF-BICARBONATO',8.3438,193.325),
    (14,'Engorde','BF-PROBIOTICO',0.0500,193.325),
    (14,'Engorde','BF-SAL-MARINA',0.0000,193.325),
    (15,'Engorde','BF-MELAZA',42.3999,227.2875),
    (15,'Engorde','BF-BICARBONATO',8.3438,227.2875),
    (15,'Engorde','BF-PROBIOTICO',0.0500,227.2875),
    (15,'Engorde','BF-SAL-MARINA',0.0000,227.2875),
    (16,'Engorde','BF-MELAZA',42.3999,261.25),
    (16,'Engorde','BF-BICARBONATO',8.3438,261.25),
    (16,'Engorde','BF-PROBIOTICO',0.0500,261.25),
    (16,'Engorde','BF-SAL-MARINA',5.5280,261.25),
    (17,'Engorde','BF-MELAZA',43.3050,295.9375),
    (17,'Engorde','BF-BICARBONATO',8.5219,295.9375),
    (17,'Engorde','BF-PROBIOTICO',0.0500,295.9375),
    (17,'Engorde','BF-SAL-MARINA',0.0000,295.9375),
    (18,'Engorde','BF-MELAZA',43.3050,330.625),
    (18,'Engorde','BF-BICARBONATO',8.5219,330.625),
    (18,'Engorde','BF-PROBIOTICO',0.0500,330.625),
    (18,'Engorde','BF-SAL-MARINA',0.0000,330.625),
    (19,'Engorde','BF-MELAZA',43.3050,365.3125),
    (19,'Engorde','BF-BICARBONATO',8.5219,365.3125),
    (19,'Engorde','BF-PROBIOTICO',0.0500,365.3125),
    (19,'Engorde','BF-SAL-MARINA',0.0000,365.3125),
    (20,'Engorde','BF-MELAZA',43.2364,400.0),
    (20,'Engorde','BF-BICARBONATO',8.5084,400.0),
    (20,'Engorde','BF-PROBIOTICO',0.0500,400.0),
    (20,'Engorde','BF-SAL-MARINA',5.5280,400.0)
) AS v(semana,fase,codigo,cantidad,biomasa)
WHERE e.nombre_comun = 'Tilapia roja'
ON CONFLICT (especie_id, semana, producto_id) DO UPDATE
SET fase = EXCLUDED.fase,
    cantidad_referencia = EXCLUDED.cantidad_referencia,
    unidad = EXCLUDED.unidad,
    base_peces = EXCLUDED.base_peces,
    biomasa_objetivo_kg = EXCLUDED.biomasa_objetivo_kg,
    observaciones = EXCLUDED.observaciones,
    activo = TRUE,
    updated_at = NOW();

COMMIT;
