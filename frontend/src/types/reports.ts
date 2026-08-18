export type Money = string | number;

export type UnidadCantidad = {
  unidad: string;
  cantidad: Money;
};

export type ReportCommon = {
  fecha_desde: string | null;
  fecha_hasta: string | null;
  total_registros: number;
  generado_en: string;
  nota?: string;
  suma_subtotales?: Money;
  n_ventas?: number;
  n_compras?: number;
  total_valor?: Money;
  suma_costo_total?: Money;
  total_costo?: Money;
  cantidad_por_unidad?: UnidadCantidad[];
  filas?: Record<string, unknown>[];
  mediciones?: Record<string, unknown>[];
  aplicaciones?: Record<string, unknown>[];
};

export type ReportId =
  | "ventas"
  | "compras"
  | "gastos"
  | "inventario"
  | "movimientos"
  | "compras-inventario"
  | "produccion"
  | "agua"
  | "biofloc"
  | "alimentacion"
  | "equipos"
  | "mantenimientos"
  | "fallas"
  | "energia"
  | "alarmas";

export type ReportFilter =
  | "fechas"
  | "lote_id"
  | "producto_id"
  | "categoria_id"
  | "cliente"
  | "proveedor"
  | "parametro_id"
  | "equipo_id"
  | "tipo_alarma_id"
  | "estado_alarma_id"
  | "clasificacion"
  | "solo_activos"
  | "activo"
  | "tipo"
  | "referencia_tipo";

export type ReportDef = {
  id: ReportId;
  path: string;
  label: string;
  filters: ReportFilter[];
  note?: string;
};

export const REPORTS: ReportDef[] = [
  { id: "ventas", path: "ventas", label: "Ventas", filters: ["fechas", "lote_id", "cliente"] },
  { id: "compras", path: "compras", label: "Compras", filters: ["fechas", "producto_id", "proveedor"] },
  {
    id: "gastos",
    path: "gastos",
    label: "Gastos",
    filters: ["fechas", "categoria_id", "lote_id", "proveedor"],
  },
  {
    id: "inventario",
    path: "inventario",
    label: "Inventario",
    filters: ["fechas", "clasificacion", "solo_activos"],
    note: "Snapshot de stock actual. fecha_desde y fecha_hasta se envían al API pero no filtran este listado.",
  },
  {
    id: "movimientos",
    path: "inventario/movimientos",
    label: "Movimientos de inventario",
    filters: ["fechas", "producto_id", "referencia_tipo"],
  },
  {
    id: "compras-inventario",
    path: "compras-inventario",
    label: "Compras → inventario",
    filters: ["fechas"],
    note: "Trazabilidad compra → detalle → movimiento con referencia_tipo DETALLE_COMPRA. No crea movimientos.",
  },
  {
    id: "produccion",
    path: "produccion",
    label: "Producción",
    filters: ["fechas", "lote_id"],
    note: "poblacion_estimada es recuento de peces (vista de biomasa). supervivencia_porcentaje y peso_promedio_g los entrega el API; no se calculan aquí.",
  },
  { id: "agua", path: "agua", label: "Agua", filters: ["fechas", "lote_id", "parametro_id"] },
  { id: "biofloc", path: "biofloc", label: "Biofloc", filters: ["fechas", "lote_id"] },
  {
    id: "alimentacion",
    path: "alimentacion",
    label: "Alimentación",
    filters: ["fechas", "lote_id"],
    note: "Alimentación no descuenta inventario. cantidad_por_unidad la entrega el API, agrupada por unidad.",
  },
  {
    id: "equipos",
    path: "equipos",
    label: "Equipos",
    filters: ["fechas", "activo"],
    note: "Snapshot de equipos. fecha_desde y fecha_hasta se envían al API pero no filtran este listado.",
  },
  { id: "mantenimientos", path: "mantenimientos", label: "Mantenimientos", filters: ["fechas", "equipo_id"] },
  { id: "fallas", path: "fallas", label: "Fallas", filters: ["fechas", "equipo_id"] },
  { id: "energia", path: "energia", label: "Energía", filters: ["fechas", "tipo"] },
  {
    id: "alarmas",
    path: "alarmas",
    label: "Alarmas",
    filters: ["fechas", "estado_alarma_id", "tipo_alarma_id"],
    note: "Alarmas generales. El stock bajo de productos está en Inventario.",
  },
];

export const CLASIFICACIONES_INVENTARIO = ["SIN_STOCK", "STOCK_BAJO", "NORMAL"] as const;
