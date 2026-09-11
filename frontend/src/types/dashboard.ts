export type PeriodoDashboard = {
  fecha_desde: string | null;
  fecha_hasta: string | null;
};

export type TotalN = {
  n: number;
  total: string | number;
};

export type DashboardResumen = {
  periodo: PeriodoDashboard;
  ventas: TotalN;
  gastos: TotalN;
  compras: TotalN;
  productos_activos: number;
  productos_sin_stock: number;
  productos_stock_bajo: number;
  alarmas_pendientes: number;
  equipos_activos: number;
  equipos_operativos: number;
  mantenimientos_periodo: number;
  eventos_energia_periodo: number;
  lotes_activos: number;
};

export type DashboardResumenParams = {
  fecha_desde?: string;
  fecha_hasta?: string;
};

export type DashboardProduccion = {
  periodo: PeriodoDashboard;
  lotes_activos: number;
  poblacion_estimada_activos: number;
  supervivencia_pct_activos: string | number | null;
  supervivencia_pct_activos_motivo: string | null;
  alimentaciones_periodo: number;
  cosechas_periodo: number;
  cosechas_peces: number;
  cosechas_peso_total_kg: string | number;
  mortalidades_periodo: number;
  mortalidades_peces: number;
  mediciones_agua_periodo: number;
  mediciones_agua_fuera_rango: number;
  mediciones_biofloc_periodo: number;
  aplicaciones_biofloc_periodo: number;
};

export type FinanzasLote = {
  lote_id: number;
  codigo: string;
  ventas: string | number;
  kg_vendidos: string | number;
  kg_cosechados: string | number;
  costo_alimento: string | number;
  gastos_lote: string | number;
  costo_produccion: string | number;
  costo_por_kg: string | number;
  costo_ventas_estimado: string | number;
  utilidad_bruta: string | number;
  margen_bruto_pct: string | number | null;
};

export type DashboardFinanzas = {
  periodo_desde: string | null;
  periodo_hasta: string | null;
  ventas: string | number;
  costo_ventas_estimado: string | number;
  utilidad_bruta: string | number;
  gastos_operativos: string | number;
  utilidad_neta: string | number;
  margen_bruto_pct: string | number | null;
  margen_neto_pct: string | number | null;
  kg_vendidos: string | number;
  costo_promedio_kg_vendido: string | number;
  costo_produccion_lotes: string | number;
  lotes_con_ventas: number;
  lotes: FinanzasLote[];
  metodologia: string;
};
