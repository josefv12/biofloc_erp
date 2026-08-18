import { apiFetch } from "./client";
import type { AnalisisLote, ComparativoEstanques } from "../types/analisis";

export type RangoFechas = {
  fechaDesde?: string;
  fechaHasta?: string;
};

export function getAnalisisLote(loteId: number, rango: RangoFechas = {}): Promise<AnalisisLote> {
  const params = new URLSearchParams();
  if (rango.fechaDesde) {
    params.set("fecha_desde", rango.fechaDesde);
  }
  if (rango.fechaHasta) {
    params.set("fecha_hasta", rango.fechaHasta);
  }
  const query = params.toString();
  return apiFetch<AnalisisLote>(`/api/v1/analisis/lotes/${loteId}${query ? `?${query}` : ""}`);
}

export function getComparativoEstanques(
  soloActivos = true,
  options: { estanqueId?: number; incluirHistorial?: boolean } = {},
): Promise<ComparativoEstanques> {
  const params = new URLSearchParams({
    solo_activos: soloActivos ? "true" : "false",
  });
  if (options.estanqueId) params.set("estanque_id", String(options.estanqueId));
  if (options.incluirHistorial) params.set("incluir_historial", "true");
  return apiFetch<ComparativoEstanques>(`/api/v1/analisis/estanques?${params.toString()}`);
}
