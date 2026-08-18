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
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function datetimeLocalToIso(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Fecha/hora inválida");
  }
  return date.toISOString();
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
