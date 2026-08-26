/** Rutas de ficha centradas en el estanque. Las pestañas heredadas se mapean en parseLoteFichaTab. */

export function pathFichaEstanque(
  estanqueId: number,
  opts?: { loteId?: number | null; tab?: string },
): string {
  const params = new URLSearchParams();
  params.set("tab", opts?.tab ?? "resumen");
  if (opts?.loteId) params.set("lote", String(opts.loteId));
  return `/produccion/estanques/${estanqueId}?${params.toString()}`;
}

export function pathFichaLote(loteId: number, tab = "resumen"): string {
  return `/produccion/lotes/${loteId}?tab=${tab}`;
}

export const PATH_COMPARACION = "/produccion/estanques";
