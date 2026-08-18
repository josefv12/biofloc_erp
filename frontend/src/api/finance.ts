import { apiFetch } from "./client";
import type { CategoriaGasto, Gasto, GastoCreate, Venta, VentaCreate } from "../types/finance";

export function listCategoriasGasto(soloActivos = true): Promise<CategoriaGasto[]> {
  return apiFetch<CategoriaGasto[]>(
    `/api/v1/categorias-gasto/?solo_activos=${soloActivos ? "true" : "false"}`,
  );
}

export function listGastos(params: {
  fechaDesde?: string;
  fechaHasta?: string;
  categoriaId?: number;
  loteId?: number;
  proveedor?: string;
} = {}): Promise<Gasto[]> {
  const query = new URLSearchParams();
  if (params.fechaDesde) query.set("fecha_desde", params.fechaDesde);
  if (params.fechaHasta) query.set("fecha_hasta", params.fechaHasta);
  if (params.categoriaId) query.set("categoria_id", String(params.categoriaId));
  if (params.loteId) query.set("lote_id", String(params.loteId));
  if (params.proveedor) query.set("proveedor", params.proveedor);
  const suffix = query.toString();
  return apiFetch<Gasto[]>(`/api/v1/gastos/${suffix ? `?${suffix}` : ""}`);
}

export function getGasto(id: number): Promise<Gasto> {
  return apiFetch<Gasto>(`/api/v1/gastos/${id}`);
}

export function createGasto(data: GastoCreate): Promise<Gasto> {
  return apiFetch<Gasto>("/api/v1/gastos/", { method: "POST", body: data });
}

export function listVentas(params: {
  fechaDesde?: string;
  fechaHasta?: string;
  cliente?: string;
  loteId?: number;
} = {}): Promise<Venta[]> {
  const query = new URLSearchParams();
  if (params.fechaDesde) query.set("fecha_desde", params.fechaDesde);
  if (params.fechaHasta) query.set("fecha_hasta", params.fechaHasta);
  if (params.cliente) query.set("cliente", params.cliente);
  if (params.loteId) query.set("lote_id", String(params.loteId));
  const suffix = query.toString();
  return apiFetch<Venta[]>(`/api/v1/ventas/${suffix ? `?${suffix}` : ""}`);
}

export function getVenta(id: number): Promise<Venta> {
  return apiFetch<Venta>(`/api/v1/ventas/${id}`);
}

export function createVenta(data: VentaCreate): Promise<Venta> {
  return apiFetch<Venta>("/api/v1/ventas/", { method: "POST", body: data });
}
