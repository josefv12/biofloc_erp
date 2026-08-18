import { apiFetch } from "./client";
import type { ReportCommon } from "../types/reports";

export type ReportParams = {
  fecha_desde?: string;
  fecha_hasta?: string;
  lote_id?: number;
  producto_id?: number;
  categoria_id?: number;
  cliente?: string;
  proveedor?: string;
  parametro_id?: number;
  equipo_id?: number;
  tipo_alarma_id?: number;
  estado_alarma_id?: number;
  clasificacion?: string;
  solo_activos?: boolean;
  activo?: boolean;
  tipo?: string;
  referencia_tipo?: string;
};

export function getReporte(path: string, params: ReportParams = {}): Promise<ReportCommon> {
  const query = new URLSearchParams();
  if (params.fecha_desde) query.set("fecha_desde", params.fecha_desde);
  if (params.fecha_hasta) query.set("fecha_hasta", params.fecha_hasta);
  if (params.lote_id) query.set("lote_id", String(params.lote_id));
  if (params.producto_id) query.set("producto_id", String(params.producto_id));
  if (params.categoria_id) query.set("categoria_id", String(params.categoria_id));
  if (params.cliente) query.set("cliente", params.cliente);
  if (params.proveedor) query.set("proveedor", params.proveedor);
  if (params.parametro_id) query.set("parametro_id", String(params.parametro_id));
  if (params.equipo_id) query.set("equipo_id", String(params.equipo_id));
  if (params.tipo_alarma_id) query.set("tipo_alarma_id", String(params.tipo_alarma_id));
  if (params.estado_alarma_id) query.set("estado_alarma_id", String(params.estado_alarma_id));
  if (params.clasificacion) query.set("clasificacion", params.clasificacion);
  if (params.solo_activos === true) query.set("solo_activos", "true");
  if (params.solo_activos === false) query.set("solo_activos", "false");
  if (params.activo === true) query.set("activo", "true");
  if (params.activo === false) query.set("activo", "false");
  if (params.tipo) query.set("tipo", params.tipo);
  if (params.referencia_tipo) query.set("referencia_tipo", params.referencia_tipo);
  const suffix = query.toString();
  return apiFetch<ReportCommon>(`/api/v1/reportes/${path}${suffix ? `?${suffix}` : ""}`);
}
