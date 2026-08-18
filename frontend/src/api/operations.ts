import { apiFetch } from "./client";
import type {
  Alimentacion,
  AlimentacionCreate,
  AplicacionBiofloc,
  AplicacionBioflocCreate,
  MedicionAgua,
  MedicionAguaCreate,
  MedicionBiofloc,
  MedicionBioflocCreate,
  ParametroAgua,
  Producto,
  ReferenciaAgua,
  TipoAplicacionBiofloc,
  Unidad,
} from "../types/operations";

export function listParametrosAgua(soloActivos = true): Promise<ParametroAgua[]> {
  return apiFetch<ParametroAgua[]>(`/api/v1/parametros-agua/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listReferenciasAgua(params: {
  especie_id?: number;
  etapa_productiva_id?: number;
  parametro_id?: number;
  solo_activos?: boolean;
} = {}): Promise<ReferenciaAgua[]> {
  const query = new URLSearchParams();
  if (params.especie_id) query.set("especie_id", String(params.especie_id));
  if (params.etapa_productiva_id) query.set("etapa_productiva_id", String(params.etapa_productiva_id));
  if (params.parametro_id) query.set("parametro_id", String(params.parametro_id));
  query.set("solo_activos", params.solo_activos === false ? "false" : "true");
  return apiFetch<ReferenciaAgua[]>(`/api/v1/referencias-agua/?${query.toString()}`);
}

export function listMedicionesAgua(params: { lote_id?: number; parametro_id?: number } = {}): Promise<MedicionAgua[]> {
  const query = new URLSearchParams();
  if (params.lote_id) query.set("lote_id", String(params.lote_id));
  if (params.parametro_id) query.set("parametro_id", String(params.parametro_id));
  const suffix = query.toString();
  return apiFetch<MedicionAgua[]>(`/api/v1/mediciones-agua/${suffix ? `?${suffix}` : ""}`);
}

export function createMedicionAgua(data: MedicionAguaCreate): Promise<MedicionAgua> {
  return apiFetch<MedicionAgua>("/api/v1/mediciones-agua/", { method: "POST", body: data });
}

export function listTiposAplicacionBiofloc(soloActivos = true): Promise<TipoAplicacionBiofloc[]> {
  return apiFetch<TipoAplicacionBiofloc[]>(
    `/api/v1/tipos-aplicacion-biofloc/?solo_activos=${soloActivos ? "true" : "false"}`,
  );
}

export function listMedicionesBiofloc(loteId?: number): Promise<MedicionBiofloc[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<MedicionBiofloc[]>(`/api/v1/mediciones-biofloc/${query}`);
}

export function createMedicionBiofloc(data: MedicionBioflocCreate): Promise<MedicionBiofloc> {
  return apiFetch<MedicionBiofloc>("/api/v1/mediciones-biofloc/", { method: "POST", body: data });
}

export function listAplicacionesBiofloc(loteId?: number): Promise<AplicacionBiofloc[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<AplicacionBiofloc[]>(`/api/v1/aplicaciones-biofloc/${query}`);
}

export function createAplicacionBiofloc(data: AplicacionBioflocCreate): Promise<AplicacionBiofloc> {
  return apiFetch<AplicacionBiofloc>("/api/v1/aplicaciones-biofloc/", { method: "POST", body: data });
}

export function listAlimentaciones(loteId?: number): Promise<Alimentacion[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<Alimentacion[]>(`/api/v1/alimentaciones/${query}`);
}

export function createAlimentacion(data: AlimentacionCreate): Promise<Alimentacion> {
  return apiFetch<Alimentacion>("/api/v1/alimentaciones/", { method: "POST", body: data });
}

export function listProductosActivos(): Promise<Producto[]> {
  return apiFetch<Producto[]>("/api/v1/productos/?solo_activos=true");
}

export function listUnidades(): Promise<Unidad[]> {
  return apiFetch<Unidad[]>("/api/v1/unidades/");
}
