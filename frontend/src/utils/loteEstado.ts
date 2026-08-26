import type { Lote } from "../types/production";

export const ESTADO_LOTE_ACTIVO = "ACTIVO";

export function esLoteActivo(lote: Lote | undefined | null): boolean {
  return lote?.estado.nombre === ESTADO_LOTE_ACTIVO;
}

export function lotesActivos(lotes: Lote[]): Lote[] {
  return lotes.filter(esLoteActivo);
}
