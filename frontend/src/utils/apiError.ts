import { ApiError } from "../api/client";

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Sesión inválida o credenciales incorrectas.";
    }
    if (error.status === 403) {
      return "No autorizado.";
    }
    if (error.status === 404) {
      return "Recurso no encontrado.";
    }
    if (error.status === 409) {
      return error.detail || "Conflicto: el recurso ya existe o no puede modificarse.";
    }
    if (error.status === 422) {
      return error.detail;
    }
    if (error.status >= 500) {
      return "No se pudo completar la operación.";
    }
    if (error.status === 0) {
      return "No se pudo conectar con el servidor.";
    }
    return error.detail;
  }
  return "No se pudo completar la operación.";
}
