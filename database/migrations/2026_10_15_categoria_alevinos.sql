-- Habilita la categoría requerida por el registro de siembra de alevinos.
SET search_path TO biofloc, public;

INSERT INTO categorias_inventario (nombre, descripcion, activo)
VALUES ('ALEVINOS', 'Alevinos vivos para siembra y producción acuícola', TRUE)
ON CONFLICT (nombre) DO UPDATE
SET descripcion = EXCLUDED.descripcion,
    activo = TRUE;
