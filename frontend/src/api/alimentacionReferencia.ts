import { apiFetch } from "./client";
import type { ReferenciaAlimentacionActiva } from "../types/analisis";

export function getContextoAlimentacionLote(loteId: number): Promise<{
  lote_id: number;
  referencia_activa: ReferenciaAlimentacionActiva | null;
  motivo: string | null;
}> {
  return apiFetch(`/api/v1/referencias-alimentacion/contexto/lotes/${loteId}`);
}
