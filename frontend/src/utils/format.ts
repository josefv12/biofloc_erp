const LOCALE = "es-CO";
const TIME_ZONE = "America/Bogota";

export function formatCop(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) {
    return "—";
  }
  return new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(
  value: number | string | null | undefined,
  options: Intl.NumberFormatOptions = {},
): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) {
    return "—";
  }
  return new Intl.NumberFormat(LOCALE, options).format(amount);
}

/** Parsea número decimal aceptando coma o punto (es-CO). Devuelve null si está vacío o es inválido. */
export function parseDecimalInput(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const normalized = trimmed.replace(",", ".");
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : null;
}

/** Valor de tooltip de gráfica: null/NaN se muestran como N/D, nunca como 0. */
export function formatChartValue(
  value: unknown,
  options: Intl.NumberFormatOptions = {},
  unidad?: string | null,
): string {
  if (value === null || value === undefined || value === "") {
    return "N/D";
  }
  const amount = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(amount)) {
    return "N/D";
  }
  return `${formatNumber(amount, options)}${unidad ? ` ${unidad}` : ""}`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = value instanceof Date ? value : parseDateOnly(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat(LOCALE, {
    timeZone: TIME_ZONE,
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function parseDateOnly(value: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T12:00:00-05:00`);
  }
  return new Date(value);
}

export function toDatetimeLocalValue(value?: string | Date | null): string {
  const date = value ? (value instanceof Date ? value : new Date(value)) : new Date();
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

export const MSG_FECHA_HORA_INVALIDA = "Fecha y hora inválidas.";

export class FechaHoraInvalidaError extends Error {
  constructor() {
    super(MSG_FECHA_HORA_INVALIDA);
    this.name = "FechaHoraInvalidaError";
  }
}

export function datetimeLocalToIso(value: string): string {
  if (!value || !value.trim()) {
    throw new FechaHoraInvalidaError();
  }
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!match) {
    throw new FechaHoraInvalidaError();
  }
  const isoBogota = `${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}:00-05:00`;
  const date = new Date(isoBogota);
  if (Number.isNaN(date.getTime())) {
    throw new FechaHoraInvalidaError();
  }
  return date.toISOString();
}

/** Convierte datetime-local a ISO. Si es inválida, avisa y no dispara la petición. */
export function withFechaHoraIso(
  value: string,
  onInvalid: (message: string) => void,
): string | null {
  try {
    return datetimeLocalToIso(value);
  } catch (err) {
    if (err instanceof FechaHoraInvalidaError) {
      onInvalid(err.message);
      return null;
    }
    throw err;
  }
}

export function uniqueById<T extends { id: number }>(items: T[]): T[] {
  const map = new Map<number, T>();
  for (const item of items) {
    map.set(item.id, item);
  }
  return [...map.values()];
}

export function formatEstado(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

/** Etiqueta legible para selectores: nombre primero, código como referencia secundaria. */
export function etiquetaProducto(nombre: string, codigo: string): string {
  return `${nombre} (Código: ${codigo})`;
}
