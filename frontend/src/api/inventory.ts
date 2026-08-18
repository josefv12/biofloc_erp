import { apiFetch } from "./client";
import type {
  AlertaStock,
  CategoriaInventario,
  MovimientoInventario,
  MovimientoInventarioCreate,
  Producto,
  ProductoCreate,
  ProductoUpdate,
  StockProducto,
  TipoMovimientoInventario,
} from "../types/inventory";

export function listCategoriasInventario(soloActivos = false): Promise<CategoriaInventario[]> {
  return apiFetch<CategoriaInventario[]>(
    `/api/v1/categorias-inventario/?solo_activos=${soloActivos ? "true" : "false"}`,
  );
}

export function listProductos(params: { soloActivos?: boolean; categoriaId?: number } = {}): Promise<Producto[]> {
  const query = new URLSearchParams();
  query.set("solo_activos", params.soloActivos ? "true" : "false");
  if (params.categoriaId) query.set("categoria_id", String(params.categoriaId));
  return apiFetch<Producto[]>(`/api/v1/productos/?${query.toString()}`);
}

export function createProducto(data: ProductoCreate): Promise<Producto> {
  return apiFetch<Producto>("/api/v1/productos/", { method: "POST", body: data });
}

export function updateProducto(id: number, data: ProductoUpdate): Promise<Producto> {
  return apiFetch<Producto>(`/api/v1/productos/${id}`, { method: "PUT", body: data });
}

export function listProductosStock(): Promise<StockProducto[]> {
  return apiFetch<StockProducto[]>("/api/v1/productos/stock");
}

export function listAlertasStockBajo(params: {
  soloActivos?: boolean;
  incluirNormal?: boolean;
  categoriaId?: number;
} = {}): Promise<AlertaStock[]> {
  const query = new URLSearchParams();
  query.set("solo_activos", params.soloActivos === false ? "false" : "true");
  if (params.incluirNormal) query.set("incluir_normal", "true");
  if (params.categoriaId) query.set("categoria_id", String(params.categoriaId));
  return apiFetch<AlertaStock[]>(`/api/v1/alertas/stock-bajo?${query.toString()}`);
}

export function listTiposMovimientoInventario(): Promise<TipoMovimientoInventario[]> {
  return apiFetch<TipoMovimientoInventario[]>("/api/v1/tipos-movimiento-inventario/");
}

export function listMovimientosInventario(params: {
  productoId?: number;
  tipoMovimientoId?: number;
  referenciaTipo?: string;
} = {}): Promise<MovimientoInventario[]> {
  const query = new URLSearchParams();
  if (params.productoId) query.set("producto_id", String(params.productoId));
  if (params.tipoMovimientoId) query.set("tipo_movimiento_id", String(params.tipoMovimientoId));
  if (params.referenciaTipo) query.set("referencia_tipo", params.referenciaTipo);
  const suffix = query.toString();
  return apiFetch<MovimientoInventario[]>(`/api/v1/movimientos-inventario/${suffix ? `?${suffix}` : ""}`);
}

export function createMovimientoInventario(data: MovimientoInventarioCreate): Promise<MovimientoInventario> {
  return apiFetch<MovimientoInventario>("/api/v1/movimientos-inventario/", { method: "POST", body: data });
}
