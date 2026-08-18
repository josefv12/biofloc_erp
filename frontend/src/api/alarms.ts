import { apiFetch } from "./client";
import type {
  Alarma,
  AlarmaCreate,
  AlarmaUpdate,
  EstadoAlarma,
  NivelAlarma,
  TipoAlarma,
} from "../types/alarms";

export function listTiposAlarma(soloActivos = false): Promise<TipoAlarma[]> {
  return apiFetch<TipoAlarma[]>(`/api/v1/tipos-alarma/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listNivelesAlarma(): Promise<NivelAlarma[]> {
  return apiFetch<NivelAlarma[]>("/api/v1/niveles-alarma/");
}

export function listEstadosAlarma(): Promise<EstadoAlarma[]> {
  return apiFetch<EstadoAlarma[]>("/api/v1/estados-alarma/");
}

export function listAlarmas(params: {
  tipoAlarmaId?: number;
  nivelAlarmaId?: number;
  estadoAlarmaId?: number;
  loteId?: number;
  equipoId?: number;
  eventoEnergiaId?: number;
  fechaDesde?: string;
  fechaHasta?: string;
} = {}): Promise<Alarma[]> {
  const query = new URLSearchParams();
  if (params.tipoAlarmaId) query.set("tipo_alarma_id", String(params.tipoAlarmaId));
  if (params.nivelAlarmaId) query.set("nivel_alarma_id", String(params.nivelAlarmaId));
  if (params.estadoAlarmaId) query.set("estado_alarma_id", String(params.estadoAlarmaId));
  if (params.loteId) query.set("lote_id", String(params.loteId));
  if (params.equipoId) query.set("equipo_id", String(params.equipoId));
  if (params.eventoEnergiaId) query.set("evento_energia_id", String(params.eventoEnergiaId));
  if (params.fechaDesde) query.set("fecha_desde", params.fechaDesde);
  if (params.fechaHasta) query.set("fecha_hasta", params.fechaHasta);
  const suffix = query.toString();
  return apiFetch<Alarma[]>(`/api/v1/alarmas/${suffix ? `?${suffix}` : ""}`);
}

export function getAlarma(id: number): Promise<Alarma> {
  return apiFetch<Alarma>(`/api/v1/alarmas/${id}`);
}

export function createAlarma(data: AlarmaCreate): Promise<Alarma> {
  return apiFetch<Alarma>("/api/v1/alarmas/", { method: "POST", body: data });
}

export function updateAlarma(id: number, data: AlarmaUpdate): Promise<Alarma> {
  return apiFetch<Alarma>(`/api/v1/alarmas/${id}`, { method: "PUT", body: data });
}
