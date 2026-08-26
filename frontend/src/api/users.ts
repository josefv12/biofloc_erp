import { apiFetch } from "./client";
import type { RolCatalogo, UsuarioCreate, UsuarioGestion, UsuarioUpdate } from "../types/auth";

export function listUsuarios(soloActivos = false): Promise<UsuarioGestion[]> {
  return apiFetch<UsuarioGestion[]>(`/api/v1/usuarios/?solo_activos=${soloActivos ? "true" : "false"}`);
}

export function getUsuario(id: number): Promise<UsuarioGestion> {
  return apiFetch<UsuarioGestion>(`/api/v1/usuarios/${id}`);
}

export function createUsuario(data: UsuarioCreate): Promise<UsuarioGestion> {
  return apiFetch<UsuarioGestion>("/api/v1/usuarios/", { method: "POST", body: data });
}

export function updateUsuario(id: number, data: UsuarioUpdate): Promise<UsuarioGestion> {
  return apiFetch<UsuarioGestion>(`/api/v1/usuarios/${id}`, { method: "PUT", body: data });
}

export function listRoles(soloActivos = true): Promise<RolCatalogo[]> {
  return apiFetch<RolCatalogo[]>(`/api/v1/roles/?solo_activos=${soloActivos ? "true" : "false"}`);
}
