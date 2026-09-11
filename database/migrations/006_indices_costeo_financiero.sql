-- Índices no destructivos para acelerar el costeo financiero por lote.
CREATE INDEX IF NOT EXISTS idx_gastos_lote_fecha
    ON biofloc.gastos (lote_id, fecha);

CREATE INDEX IF NOT EXISTS idx_alimentaciones_lote_fecha
    ON biofloc.alimentaciones (lote_id, fecha_hora);

CREATE INDEX IF NOT EXISTS idx_compras_fecha
    ON biofloc.compras (fecha);

CREATE INDEX IF NOT EXISTS idx_detalles_compra_producto_compra
    ON biofloc.detalles_compra (producto_id, compra_id);

CREATE INDEX IF NOT EXISTS idx_detalles_venta_lote_venta
    ON biofloc.detalles_venta (lote_id, venta_id);

CREATE INDEX IF NOT EXISTS idx_cosechas_lote_fecha
    ON biofloc.cosechas (lote_id, fecha_hora);
