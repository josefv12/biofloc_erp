export type PeriodoDashboard = {
  fecha_desde: string | null;
  fecha_hasta: string | null;
};

export type TotalN = {
  n: number;
  total: string | number;
};

/** Contrato exacto de GET /api/v1/dashboard/resumen */
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
