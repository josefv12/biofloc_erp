import { apiFetch } from "./client";
import { listProductos } from "./inventory";
import { listUnidades } from "./operations";
import { cantidadParaPresentacion, precioParaPresentacion, unidadPresentacion } from "../utils/unidades";
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

const REPORTES_CON_PRODUCTOS = new Set(["compras", "inventario", "movimientos", "compras-inventario", "alimentacion"]);

type ReportRow = Record<string, unknown>;

function numero(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

async function presentarUnidades(path: string, result: ReportCommon): Promise<ReportCommon> {
  if (!REPORTES_CON_PRODUCTOS.has(path)) return result;

  const filas = (result as unknown as { filas?: ReportRow[] }).filas;
  if (!Array.isArray(filas) || filas.length === 0) return result;

  const [productos, unidades] = await Promise.all([listProductos({ soloActivos: false }), listUnidades()]);
  const productosMap = new Map(productos.map((producto) => [producto.id, producto]));
  const unidadesMap = new Map(unidades.map((unidad) => [unidad.id, unidad]));

  const filasPresentadas = filas.map((row) => {
    const productoId = numero(row.producto_id);
    const producto = productoId == null ? undefined : productosMap.get(productoId);
    if (!producto) return row;

    const simboloInterno = unidadesMap.get(producto.unidad_id)?.simbolo;
    const simboloComercial = unidadesMap.get(producto.unidad_comercial_id)?.simbolo;
    const factor = producto.factor_conversion;
    const next: ReportRow = { ...row };

    const cantidad = numero(row.cantidad);
    if (cantidad !== null) {
      next.cantidad = cantidadParaPresentacion(cantidad, simboloInterno, factor);
    }

    const stockActual = numero(row.stock_actual);
    if (stockActual !== null) {
      next.stock_actual = cantidadParaPresentacion(stockActual, simboloInterno, factor);
    }

    const stockMinimo = numero(row.stock_minimo);
    if (stockMinimo !== null) {
      next.stock_minimo = cantidadParaPresentacion(stockMinimo, simboloInterno, factor);
    }

    const precioUnitario = numero(row.precio_unitario);
    if (precioUnitario !== null) {
      next.precio_unitario = precioParaPresentacion(precioUnitario, simboloInterno, factor);
    }

    const costoUnitario = numero(row.costo_unitario);
    if (costoUnitario !== null) {
      next.costo_unitario = precioParaPresentacion(costoUnitario, simboloInterno, factor);
    }

    if (simboloInterno || simboloComercial) {
      next.unidad = unidadPresentacion(simboloInterno, simboloComercial);
    }
    return next;
  });

  return { ...result, filas: filasPresentadas } as ReportCommon;
}

export async function getReporte(path: string, params: ReportParams = {}): Promise<ReportCommon> {
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
  const result = await apiFetch<ReportCommon>(`/api/v1/reportes/${path}${suffix ? `?${suffix}` : ""}`);
  return presentarUnidades(path, result);
}
