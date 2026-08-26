/**
 * Etiquetas para rangos almacenados en referencias_produccion.
 *
 * semana_desde / semana_hasta son el almacenamiento interno.
 * La semana del lote la calcula el backend: floor(días / 7) + 1.
 * Aquí solo se formatea el rango tal como está guardado; no se convierte 0 → 1.
 */
export function etiquetaSemanaProductiva(semana: number): string {
  return `Semana ${semana}`;
}

/** Muestra un rango [semana_desde, semana_hasta] como semana(s) del catálogo. */
export function etiquetaRangoSemanas(desde: number, hasta: number): string {
  if (desde === hasta) return etiquetaSemanaProductiva(desde);
  return `Semanas ${desde}–${hasta}`;
}

/** Raciones literales: 6 y 8 → "6–8 raciones/día". Nunca un promedio. */
export function etiquetaRaciones(min: number | null | undefined, max: number | null | undefined): string {
  if (min == null && max == null) return "N/D";
  if (min == null) return `${max} raciones/día`;
  if (max == null || min === max) return `${min} raciones/día`;
  return `${min}–${max} raciones/día`;
}

export function etiquetaRacionesCatalogo(
  min: number | null | undefined,
  max: number | null | undefined,
  texto?: string | null,
): string {
  if (min != null || max != null) return etiquetaRaciones(min, max);
  if (texto && texto !== "N/D") {
    return texto.includes("racion") ? texto : `${texto} raciones/día`;
  }
  return "N/D";
}
