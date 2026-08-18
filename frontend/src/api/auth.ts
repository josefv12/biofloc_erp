import { apiFetch } from "./client";
import type { LoginRequest, TokenResponse, UsuarioActual } from "../types/auth";

export function loginRequest(data: LoginRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: data,
  });
}

export function meRequest(): Promise<UsuarioActual> {
  return apiFetch<UsuarioActual>("/api/v1/auth/me");
}

export function healthRequest(): Promise<{ api: string; database: string }> {
  return apiFetch<{ api: string; database: string }>("/health");
}
