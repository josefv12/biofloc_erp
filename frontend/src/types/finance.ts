export type CategoriaGasto = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type Gasto = {
  id: number;
  fecha: string;
  categoria_id: number;
  lote_id: number | null;
  descripcion: string;
  valor: string | number;
  proveedor: string | null;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
};

export type GastoCreate = {
  fecha: string;
  categoria_id: number;
  lote_id?: number | null;
  descripcion: string;
  valor: number;
  proveedor?: string | null;
  observaciones?: string | null;
};

export type DetalleVenta = {
  id: number;
  venta_id: number;
  lote_id: number;
  cantidad: string | number;
  precio_unitario: string | number;
  subtotal: string | number;
};

export type DetalleVentaCreate = {
  lote_id: number;
  cantidad: number;
  precio_unitario: number;
};

export type Venta = {
  id: number;
  fecha: string;
  cliente: string | null;
  observaciones: string | null;
  total: string | number;
  registrado_por: number;
  created_at: string;
  detalles: DetalleVenta[];
};

export type VentaCreate = {
  fecha: string;
  cliente?: string | null;
  observaciones?: string | null;
  detalles: DetalleVentaCreate[];
};
