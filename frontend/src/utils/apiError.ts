import { ApiError } from "../api/client";
import { FechaHoraInvalidaError, MSG_FECHA_HORA_INVALIDA } from "./format";

const MSG_ERROR_INTERNO = "Ocurrió un error interno al procesar la operación.";

function logTecnico(contexto: string, error: unknown): void {
  if (import.meta.env.DEV) {
    console.error(`[biofloc] ${contexto}`, error);
  }
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof FechaHoraInvalidaError) {
    return MSG_FECHA_HORA_INVALIDA;
  }
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
      logTecnico(`HTTP ${error.status}`, error);
      return MSG_ERROR_INTERNO;
    }
    if (error.status === 0) {
      return "No se pudo conectar con el servidor.";
    }
    return error.detail;
  }
  logTecnico("error no HTTP", error);
  return MSG_ERROR_INTERNO;
}
