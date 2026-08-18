import { apiFetch } from "./client";
import type { DashboardProduccion, DashboardResumen, DashboardResumenParams } from "../types/dashboard";

export function fetchDashboardResumen(params: DashboardResumenParams = {}): Promise<DashboardResumen> {
  const query = new URLSearchParams();
  if (params.fecha_desde) {
    query.set("fecha_desde", params.fecha_desde);
  }
  if (params.fecha_hasta) {
    query.set("fecha_hasta", params.fecha_hasta);
  }
  const suffix = query.toString();
  return apiFetch<DashboardResumen>(`/api/v1/dashboard/resumen${suffix ? `?${suffix}` : ""}`);
}

export function fetchDashboardProduccion(
  params: DashboardResumenParams = {},
): Promise<DashboardProduccion> {
  const query = new URLSearchParams();
  if (params.fecha_desde) query.set("fecha_desde", params.fecha_desde);
  if (params.fecha_hasta) query.set("fecha_hasta", params.fecha_hasta);
  const suffix = query.toString();
  return apiFetch<DashboardProduccion>(
    `/api/v1/dashboard/produccion${suffix ? `?${suffix}` : ""}`,
  );
}
