import { apiFetch } from "./client";
import type {
  Biometria,
  BiometriaCreate,
  Cosecha,
  CosechaCreate,
  Estanque,
  EstanqueCreate,
  EstanqueUpdate,
  Lote,
  LoteCreate,
  LoteUpdate,
  Mortalidad,
  MortalidadCreate,
} from "../types/production";

export function listEstanques(soloActivos = true): Promise<Estanque[]> {
  return apiFetch<Estanque[]>(`/api/v1/estanques/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function getEstanque(id: number): Promise<Estanque> {
  return apiFetch<Estanque>(`/api/v1/estanques/${id}`);
}

export function createEstanque(data: EstanqueCreate): Promise<Estanque> {
  return apiFetch<Estanque>("/api/v1/estanques/", { method: "POST", body: data });
}

export function updateEstanque(id: number, data: EstanqueUpdate): Promise<Estanque> {
  return apiFetch<Estanque>(`/api/v1/estanques/${id}`, { method: "PUT", body: data });
}

export function listLotes(estanqueId?: number): Promise<Lote[]> {
  const query = estanqueId ? `?estanque_id=${estanqueId}` : "";
  return apiFetch<Lote[]>(`/api/v1/lotes/${query}`);
}

export function getLote(id: number): Promise<Lote> {
  return apiFetch<Lote>(`/api/v1/lotes/${id}`);
}

export function createLote(data: LoteCreate): Promise<Lote> {
  return apiFetch<Lote>("/api/v1/lotes/", { method: "POST", body: data });
}

export function updateLote(id: number, data: LoteUpdate): Promise<Lote> {
  return apiFetch<Lote>(`/api/v1/lotes/${id}`, { method: "PUT", body: data });
}

export function listBiometrias(loteId?: number): Promise<Biometria[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<Biometria[]>(`/api/v1/biometrias/${query}`);
}

export function createBiometria(data: BiometriaCreate): Promise<Biometria> {
  return apiFetch<Biometria>("/api/v1/biometrias/", { method: "POST", body: data });
}

export function listMortalidades(loteId?: number): Promise<Mortalidad[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<Mortalidad[]>(`/api/v1/mortalidades/${query}`);
}

export function createMortalidad(data: MortalidadCreate): Promise<Mortalidad> {
  return apiFetch<Mortalidad>("/api/v1/mortalidades/", { method: "POST", body: data });
}

export function listCosechas(loteId?: number): Promise<Cosecha[]> {
  const query = loteId ? `?lote_id=${loteId}` : "";
  return apiFetch<Cosecha[]>(`/api/v1/cosechas/${query}`);
}

export function createCosecha(data: CosechaCreate): Promise<Cosecha> {
  return apiFetch<Cosecha>("/api/v1/cosechas/", { method: "POST", body: data });
}
