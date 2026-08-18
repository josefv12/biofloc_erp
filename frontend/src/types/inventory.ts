export type { Producto, Unidad } from "./operations";

export type CategoriaInventario = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type ProductoCreate = {
  codigo: string;
  nombre: string;
  categoria_id: number;
  unidad_id: number;
  stock_minimo: number;
  activo?: boolean;
};

export type ProductoUpdate = {
  codigo?: string;
  nombre?: string;
  categoria_id?: number;
  unidad_id?: number;
  stock_minimo?: number;
  activo?: boolean;
};

export type StockProducto = {
  producto_id: number;
  codigo: string;
  nombre: string;
  unidad: string;
  stock_actual: string | number;
  stock_minimo: string | number;
};

export type ClasificacionStock = "SIN_STOCK" | "STOCK_BAJO" | "NORMAL";

export type AlertaStock = {
  producto_id: number;
  codigo: string;
  nombre: string;
  unidad: string;
  stock_actual: string | number;
  stock_minimo: string | number;
  diferencia: string | number;
  clasificacion: string;
  activo: boolean;
  categoria_id: number;
  categoria_nombre: string | null;
};

export type TipoMovimientoInventario = {
  id: number;
  nombre: string;
  descripcion: string | null;
  afecta_stock: -1 | 1;
};

export type MovimientoInventario = {
  id: number;
  producto_id: number;
  tipo_movimiento_id: number;
  cantidad: string | number;
  fecha_hora: string;
  referencia_tipo: string | null;
  referencia_id: number | null;
  observaciones: string | null;
  costo_unitario: string | number | null;
  costo_total: string | number | null;
  registrado_por: number;
  created_at: string;
};

export type MovimientoInventarioCreate = {
  producto_id: number;
  tipo_movimiento_id: number;
  cantidad: number;
  fecha_hora?: string | null;
  referencia_tipo?: string | null;
  referencia_id?: number | null;
  observaciones?: string | null;
  costo_unitario?: number | null;
  costo_total?: number | null;
};
