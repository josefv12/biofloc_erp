const TOKEN_KEY = "biofloc_access_token";

export const UNAUTHORIZED_EVENT = "biofloc:unauthorized";

// In production the frontend talks directly to the Render API.
// In local development Vite can override this with VITE_API_BASE_URL.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "https://biofloc-erp.onrender.com").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(detail: string, status: number) {
    super(detail);
    this.name = "ApiError";
    this.detail = detail;
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function defaultMessage(status: number): string {
  switch (status) {
    case 401:
      return "Sesión inválida o credenciales incorrectas.";
    case 403:
      return "No tiene permiso para esta operación.";
    case 404:
      return "Recurso no encontrado.";
    case 409:
      return "Conflicto: el recurso ya existe o no puede modificarse.";
    case 422:
      return "Los datos enviados no son válidos.";
    default:
      if (status >= 500) {
        return "Ocurrió un error interno al procesar la operación.";
      }
      return "No se pudo completar la operación.";
  }
}

function looksLikeInternalError(message: string): boolean {
  return /psycopg|sqlalchemy|IntegrityError|UniqueViolation|OperationalError|Traceback|postgresql/i.test(
    message,
  );
}

function parseDetail(payload: unknown, status: number): string {
  if (!payload || typeof payload !== "object") {
    return defaultMessage(status);
  }

  const detail = (payload as { detail?: unknown }).detail;

  let message: string;
  if (typeof detail === "string") {
    message = detail;
  } else if (Array.isArray(detail)) {
    message = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter((part): part is string => Boolean(part))
      .join(". ");
    if (!message) {
      message = defaultMessage(status);
    }
  } else {
    message = defaultMessage(status);
  }

  if (looksLikeInternalError(message)) {
    if (import.meta.env.DEV) {
      console.error("[biofloc] detalle técnico filtrado", { status, message });
    }
    return defaultMessage(status);
  }
  return message;
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined && options.body !== null) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body,
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor.", 0);
  }

  const isJson = (response.headers.get("content-type") ?? "").includes("application/json");
  const payload: unknown = isJson ? await response.json().catch(() => null) : null;

  if (response.status === 401) {
    const isLogin = path.includes("/auth/login");
    if (!isLogin) {
      clearToken();
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new ApiError(parseDetail(payload, 401), 401);
  }

  if (!response.ok) {
    const sinCuerpo = payload == null;
    if (sinCuerpo && (response.status === 0 || response.status >= 500)) {
      throw new ApiError("No se pudo conectar con el servidor.", 0);
    }
    throw new ApiError(parseDetail(payload, response.status), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return payload as T;
}
