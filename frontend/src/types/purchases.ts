export type DetalleCompra = {
  id: number;
  compra_id: number;
  producto_id: number;
  cantidad: string | number;
  precio_unitario: string | number;
  subtotal: string | number;
};

export type DetalleCompraIn = {
  producto_id: number;
  cantidad: number;
  precio_unitario: number;
};

export type Compra = {
  id: number;
  fecha: string;
  proveedor: string | null;
  total: string | number;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
  detalles: DetalleCompra[];
};

export type MovimientoCompraAsociado = {
  id: number;
  producto_id: number;
  tipo_movimiento_id: number;
  cantidad: number | string | null;
  fecha_hora: string | null;
  referencia_tipo: string | null;
  referencia_id: number | null;
  observaciones: string | null;
  registrado_por: number;
  costo_unitario: number | string | null;
  costo_total: number | string | null;
};

export type CompraDetalle = Compra & {
  movimientos: MovimientoCompraAsociado[];
};

export type CompraCreate = {
  fecha: string;
  proveedor?: string | null;
  observaciones?: string | null;
  detalles: DetalleCompraIn[];
};
