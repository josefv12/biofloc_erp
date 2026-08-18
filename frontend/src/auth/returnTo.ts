/** Ruta interna a la que volver tras login. Rechaza URLs abiertas o el propio login. */
export function returnToPath(from: unknown): string {
  if (typeof from !== "string") {
    return "/dashboard";
  }
  if (!from.startsWith("/") || from.startsWith("//") || from.startsWith("/login")) {
    return "/dashboard";
  }
  return from;
}
