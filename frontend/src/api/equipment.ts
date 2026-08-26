import { apiFetch } from "./client";
import type {
  Equipo,
  EquipoCreate,
  EquipoUpdate,
  EstadoEquipo,
  EventoEnergia,
  EventoEnergiaCreate,
  EventoEnergiaUpdate,
  Falla,
  FallaCreate,
  FallaUpdate,
  Mantenimiento,
  MantenimientoCreate,
  TipoEquipo,
  TipoMantenimiento,
} from "../types/equipment";

export function listTiposEquipo(soloActivos = false): Promise<TipoEquipo[]> {
  return apiFetch<TipoEquipo[]>(`/api/v1/tipos-equipo/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listEstadosEquipo(soloActivos = false): Promise<EstadoEquipo[]> {
  return apiFetch<EstadoEquipo[]>(`/api/v1/estados-equipo/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function listEquipos(params: {
  soloActivos?: boolean;
  tipoEquipoId?: number;
  estadoId?: number;
  codigo?: string;
  nombre?: string;
} = {}): Promise<Equipo[]> {
  const query = new URLSearchParams();
  query.set("solo_activos", params.soloActivos ? "true" : "false");
  if (params.tipoEquipoId) query.set("tipo_equipo_id", String(params.tipoEquipoId));
  if (params.estadoId) query.set("estado_id", String(params.estadoId));
  if (params.codigo) query.set("codigo", params.codigo);
  if (params.nombre) query.set("nombre", params.nombre);
  return apiFetch<Equipo[]>(`/api/v1/equipos/?${query.toString()}`);
}

export function createEquipo(data: EquipoCreate): Promise<Equipo> {
  return apiFetch<Equipo>("/api/v1/equipos/", { method: "POST", body: data });
}

export function updateEquipo(id: number, data: EquipoUpdate): Promise<Equipo> {
  return apiFetch<Equipo>(`/api/v1/equipos/${id}`, { method: "PUT", body: data });
}

export function listTiposMantenimiento(soloActivos = false): Promise<TipoMantenimiento[]> {
  return apiFetch<TipoMantenimiento[]>(
    `/api/v1/tipos-mantenimiento/?solo_activos=${soloActivos ? "true" : "false"}`,
  );
}

export function listMantenimientos(params: {
  equipoId?: number;
  tipoMantenimientoId?: number;
  fechaDesde?: string;
  fechaHasta?: string;
} = {}): Promise<Mantenimiento[]> {
  const query = new URLSearchParams();
  if (params.equipoId) query.set("equipo_id", String(params.equipoId));
  if (params.tipoMantenimientoId) query.set("tipo_mantenimiento_id", String(params.tipoMantenimientoId));
  if (params.fechaDesde) query.set("fecha_desde", params.fechaDesde);
  if (params.fechaHasta) query.set("fecha_hasta", params.fechaHasta);
  const suffix = query.toString();
  return apiFetch<Mantenimiento[]>(`/api/v1/mantenimientos/${suffix ? `?${suffix}` : ""}`);
}

export function createMantenimiento(data: MantenimientoCreate): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>("/api/v1/mantenimientos/", { method: "POST", body: data });
}

export function listFallas(params: { equipoId?: number } = {}): Promise<Falla[]> {
  const query = params.equipoId ? `?equipo_id=${params.equipoId}` : "";
  return apiFetch<Falla[]>(`/api/v1/fallas/${query}`);
}

export function createFalla(data: FallaCreate): Promise<Falla> {
  return apiFetch<Falla>("/api/v1/fallas/", { method: "POST", body: data });
}

export function updateFalla(id: number, data: FallaUpdate): Promise<Falla> {
  return apiFetch<Falla>(`/api/v1/fallas/${id}`, { method: "PUT", body: data });
}

export function listEventosEnergia(params: {
  tipo?: string;
  respaldoActivado?: boolean;
  equipoRespaldoId?: number;
} = {}): Promise<EventoEnergia[]> {
  const query = new URLSearchParams();
  if (params.tipo) query.set("tipo", params.tipo);
  if (params.respaldoActivado === true) query.set("respaldo_activado", "true");
  if (params.respaldoActivado === false) query.set("respaldo_activado", "false");
  if (params.equipoRespaldoId) query.set("equipo_respaldo_id", String(params.equipoRespaldoId));
  const suffix = query.toString();
  return apiFetch<EventoEnergia[]>(`/api/v1/eventos-energia/${suffix ? `?${suffix}` : ""}`);
}

export function createEventoEnergia(data: EventoEnergiaCreate): Promise<EventoEnergia> {
  return apiFetch<EventoEnergia>("/api/v1/eventos-energia/", { method: "POST", body: data });
}

export function updateEventoEnergia(id: number, data: EventoEnergiaUpdate): Promise<EventoEnergia> {
  return apiFetch<EventoEnergia>(`/api/v1/eventos-energia/${id}`, { method: "PUT", body: data });
}
