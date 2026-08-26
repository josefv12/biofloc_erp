import { apiFetch } from "./client";
import type {
  Biometria,
  BiometriaCreate,
  Cosecha,
  CosechaCreate,
  EspecieCatalogo,
  EspecieCreate,
  EspecieUpdate,
  EstadoLoteCatalogo,
  EstadoEstanque,
  Estanque,
  EstanqueCreate,
  EstanqueUpdate,
  EtapaProductivaCatalogo,
  Lote,
  LoteCreate,
  LoteUpdate,
  Mortalidad,
  MortalidadCreate,
  ReferenciaProduccion,
  ReferenciaProduccionCreate,
  ReferenciaProduccionUpdate,
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

export function listEspecies(soloActivos = false): Promise<EspecieCatalogo[]> {
  return apiFetch<EspecieCatalogo[]>(`/api/v1/especies/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function createEspecie(data: EspecieCreate): Promise<EspecieCatalogo> {
  return apiFetch<EspecieCatalogo>("/api/v1/especies/", { method: "POST", body: data });
}

export function updateEspecie(id: number, data: EspecieUpdate): Promise<EspecieCatalogo> {
  return apiFetch<EspecieCatalogo>(`/api/v1/especies/${id}`, { method: "PUT", body: data });
}

export function listEtapasProductivas(soloActivos = false): Promise<EtapaProductivaCatalogo[]> {
  return apiFetch<EtapaProductivaCatalogo[]>(
    `/api/v1/etapas-productivas/?solo_activos=${soloActivos ? "true" : "false"}`,
  );
}

export function listEstadosLote(soloActivos = false): Promise<EstadoLoteCatalogo[]> {
  return apiFetch<EstadoLoteCatalogo[]>(`/api/v1/estados-lote/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listEstadosEstanque(soloActivos = false): Promise<EstadoEstanque[]> {
  return apiFetch<EstadoEstanque[]>(`/api/v1/estados-estanque/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listReferenciasProduccion(params: {
  especie_id?: number;
  etapa_productiva_id?: number;
  semana?: number;
  solo_activos?: boolean;
} = {}): Promise<ReferenciaProduccion[]> {
  const query = new URLSearchParams();
  if (params.especie_id) query.set("especie_id", String(params.especie_id));
  if (params.etapa_productiva_id) query.set("etapa_productiva_id", String(params.etapa_productiva_id));
  if (params.semana != null) query.set("semana", String(params.semana));
  query.set("solo_activos", params.solo_activos === false ? "false" : "true");
  return apiFetch<ReferenciaProduccion[]>(`/api/v1/referencias-produccion/?${query.toString()}`);
}

export function createReferenciaProduccion(data: ReferenciaProduccionCreate): Promise<ReferenciaProduccion> {
  return apiFetch<ReferenciaProduccion>("/api/v1/referencias-produccion/", { method: "POST", body: data });
}

export function updateReferenciaProduccion(
  id: number,
  data: ReferenciaProduccionUpdate,
): Promise<ReferenciaProduccion> {
  return apiFetch<ReferenciaProduccion>(`/api/v1/referencias-produccion/${id}`, { method: "PUT", body: data });
}
