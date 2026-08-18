import { apiFetch } from "./client";
import type { Compra, CompraCreate, CompraDetalle } from "../types/purchases";

export function listCompras(params: {
  fechaDesde?: string;
  fechaHasta?: string;
  proveedor?: string;
  productoId?: number;
} = {}): Promise<Compra[]> {
  const query = new URLSearchParams();
  if (params.fechaDesde) query.set("fecha_desde", params.fechaDesde);
  if (params.fechaHasta) query.set("fecha_hasta", params.fechaHasta);
  if (params.proveedor) query.set("proveedor", params.proveedor);
  if (params.productoId) query.set("producto_id", String(params.productoId));
  const suffix = query.toString();
  return apiFetch<Compra[]>(`/api/v1/compras/${suffix ? `?${suffix}` : ""}`);
}

export function getCompra(id: number): Promise<CompraDetalle> {
  return apiFetch<CompraDetalle>(`/api/v1/compras/${id}`);
}

export function createCompra(data: CompraCreate): Promise<Compra> {
  return apiFetch<Compra>("/api/v1/compras/", { method: "POST", body: data });
}
