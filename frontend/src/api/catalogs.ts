import { apiFetch } from "./client";
import type { EstadoAlarma, NivelAlarma, TipoAlarma } from "../types/alarms";
import type { EstadoEquipo, TipoEquipo, TipoMantenimiento } from "../types/equipment";
import type { CategoriaGasto } from "../types/finance";
import type { CategoriaInventario, TipoMovimientoInventario } from "../types/inventory";
import type {
  ParametroAgua,
  ReferenciaAgua,
  ReferenciaBiofloc,
  ReferenciaBioflocCreate,
  ReferenciaBioflocUpdate,
  TipoAplicacionBiofloc,
  Unidad,
} from "../types/operations";

export type NombreDescripcionActivoCreate = {
  nombre: string;
  descripcion?: string | null;
  activo?: boolean;
};

export type NombreDescripcionActivoUpdate = {
  nombre?: string;
  descripcion?: string | null;
  activo?: boolean;
};

export type ParametroAguaCreate = {
  nombre: string;
  unidad: string;
  descripcion?: string | null;
  activo?: boolean;
};

export type ParametroAguaUpdate = {
  nombre?: string;
  unidad?: string;
  descripcion?: string | null;
  activo?: boolean;
};

export type ReferenciaAguaCreate = {
  especie_id: number;
  etapa_productiva_id: number;
  parametro_id: number;
  valor_minimo?: number | null;
  valor_maximo?: number | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type ReferenciaAguaUpdate = {
  valor_minimo?: number | null;
  valor_maximo?: number | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type UnidadCreate = {
  nombre: string;
  simbolo: string;
  activo?: boolean;
};

export type UnidadUpdate = {
  nombre?: string;
  simbolo?: string;
  activo?: boolean;
};

export type TipoMovimientoCreate = {
  nombre: string;
  descripcion?: string | null;
  afecta_stock: -1 | 1;
};

export type TipoMovimientoUpdate = {
  nombre?: string;
  descripcion?: string | null;
  afecta_stock?: -1 | 1;
};

export type NivelAlarmaCreate = {
  nombre: string;
  prioridad: number;
};

export type NivelAlarmaUpdate = {
  nombre?: string;
  prioridad?: number;
};

export type EstadoAlarmaCreate = {
  nombre: string;
  descripcion?: string | null;
};

export type EstadoAlarmaUpdate = {
  nombre?: string;
  descripcion?: string | null;
};

export function createParametroAgua(data: ParametroAguaCreate): Promise<ParametroAgua> {
  return apiFetch<ParametroAgua>("/api/v1/parametros-agua/", { method: "POST", body: data });
}

export function updateParametroAgua(id: number, data: ParametroAguaUpdate): Promise<ParametroAgua> {
  return apiFetch<ParametroAgua>(`/api/v1/parametros-agua/${id}`, { method: "PUT", body: data });
}

export function createReferenciaAgua(data: ReferenciaAguaCreate): Promise<ReferenciaAgua> {
  return apiFetch<ReferenciaAgua>("/api/v1/referencias-agua/", { method: "POST", body: data });
}

export function updateReferenciaAgua(id: number, data: ReferenciaAguaUpdate): Promise<ReferenciaAgua> {
  return apiFetch<ReferenciaAgua>(`/api/v1/referencias-agua/${id}`, { method: "PUT", body: data });
}

export function createReferenciaBiofloc(data: ReferenciaBioflocCreate): Promise<ReferenciaBiofloc> {
  return apiFetch<ReferenciaBiofloc>("/api/v1/referencias-biofloc/", { method: "POST", body: data });
}

export function updateReferenciaBiofloc(id: number, data: ReferenciaBioflocUpdate): Promise<ReferenciaBiofloc> {
  return apiFetch<ReferenciaBiofloc>(`/api/v1/referencias-biofloc/${id}`, { method: "PUT", body: data });
}

export function createTipoAplicacionBiofloc(data: NombreDescripcionActivoCreate): Promise<TipoAplicacionBiofloc> {
  return apiFetch<TipoAplicacionBiofloc>("/api/v1/tipos-aplicacion-biofloc/", { method: "POST", body: data });
}

export function updateTipoAplicacionBiofloc(
  id: number,
  data: NombreDescripcionActivoUpdate,
): Promise<TipoAplicacionBiofloc> {
  return apiFetch<TipoAplicacionBiofloc>(`/api/v1/tipos-aplicacion-biofloc/${id}`, { method: "PUT", body: data });
}

export function createCategoriaInventario(data: NombreDescripcionActivoCreate): Promise<CategoriaInventario> {
  return apiFetch<CategoriaInventario>("/api/v1/categorias-inventario/", { method: "POST", body: data });
}

export function updateCategoriaInventario(
  id: number,
  data: NombreDescripcionActivoUpdate,
): Promise<CategoriaInventario> {
  return apiFetch<CategoriaInventario>(`/api/v1/categorias-inventario/${id}`, { method: "PUT", body: data });
}

export function createUnidad(data: UnidadCreate): Promise<Unidad> {
  return apiFetch<Unidad>("/api/v1/unidades/", { method: "POST", body: data });
}

export function updateUnidad(id: number, data: UnidadUpdate): Promise<Unidad> {
  return apiFetch<Unidad>(`/api/v1/unidades/${id}`, { method: "PUT", body: data });
}

export function createTipoMovimientoInventario(data: TipoMovimientoCreate): Promise<TipoMovimientoInventario> {
  return apiFetch<TipoMovimientoInventario>("/api/v1/tipos-movimiento-inventario/", {
    method: "POST",
    body: data,
  });
}

export function updateTipoMovimientoInventario(
  id: number,
  data: TipoMovimientoUpdate,
): Promise<TipoMovimientoInventario> {
  return apiFetch<TipoMovimientoInventario>(`/api/v1/tipos-movimiento-inventario/${id}`, {
    method: "PUT",
    body: data,
  });
}

export function createCategoriaGasto(data: NombreDescripcionActivoCreate): Promise<CategoriaGasto> {
  return apiFetch<CategoriaGasto>("/api/v1/categorias-gasto/", { method: "POST", body: data });
}

export function updateCategoriaGasto(id: number, data: NombreDescripcionActivoUpdate): Promise<CategoriaGasto> {
  return apiFetch<CategoriaGasto>(`/api/v1/categorias-gasto/${id}`, { method: "PUT", body: data });
}

export function createTipoEquipo(data: NombreDescripcionActivoCreate): Promise<TipoEquipo> {
  return apiFetch<TipoEquipo>("/api/v1/tipos-equipo/", { method: "POST", body: data });
}

export function updateTipoEquipo(id: number, data: NombreDescripcionActivoUpdate): Promise<TipoEquipo> {
  return apiFetch<TipoEquipo>(`/api/v1/tipos-equipo/${id}`, { method: "PUT", body: data });
}

export function createEstadoEquipo(data: NombreDescripcionActivoCreate): Promise<EstadoEquipo> {
  return apiFetch<EstadoEquipo>("/api/v1/estados-equipo/", { method: "POST", body: data });
}

export function updateEstadoEquipo(id: number, data: NombreDescripcionActivoUpdate): Promise<EstadoEquipo> {
  return apiFetch<EstadoEquipo>(`/api/v1/estados-equipo/${id}`, { method: "PUT", body: data });
}

export function createTipoMantenimiento(data: NombreDescripcionActivoCreate): Promise<TipoMantenimiento> {
  return apiFetch<TipoMantenimiento>("/api/v1/tipos-mantenimiento/", { method: "POST", body: data });
}

export function updateTipoMantenimiento(id: number, data: NombreDescripcionActivoUpdate): Promise<TipoMantenimiento> {
  return apiFetch<TipoMantenimiento>(`/api/v1/tipos-mantenimiento/${id}`, { method: "PUT", body: data });
}

export function createTipoAlarma(data: NombreDescripcionActivoCreate): Promise<TipoAlarma> {
  return apiFetch<TipoAlarma>("/api/v1/tipos-alarma/", { method: "POST", body: data });
}

export function updateTipoAlarma(id: number, data: NombreDescripcionActivoUpdate): Promise<TipoAlarma> {
  return apiFetch<TipoAlarma>(`/api/v1/tipos-alarma/${id}`, { method: "PUT", body: data });
}

export function createNivelAlarma(data: NivelAlarmaCreate): Promise<NivelAlarma> {
  return apiFetch<NivelAlarma>("/api/v1/niveles-alarma/", { method: "POST", body: data });
}

export function updateNivelAlarma(id: number, data: NivelAlarmaUpdate): Promise<NivelAlarma> {
  return apiFetch<NivelAlarma>(`/api/v1/niveles-alarma/${id}`, { method: "PUT", body: data });
}

export function createEstadoAlarma(data: EstadoAlarmaCreate): Promise<EstadoAlarma> {
  return apiFetch<EstadoAlarma>("/api/v1/estados-alarma/", { method: "POST", body: data });
}

export function updateEstadoAlarma(id: number, data: EstadoAlarmaUpdate): Promise<EstadoAlarma> {
  return apiFetch<EstadoAlarma>(`/api/v1/estados-alarma/${id}`, { method: "PUT", body: data });
}
