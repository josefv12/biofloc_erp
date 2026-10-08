export type CostoLoteDetalle = {
  fecha: string;
  categoria: string;
  concepto: string;
  cantidad: string | number | null;
  unidad: string | null;
  costo_unitario: string | number | null;
  costo_total: string | number;
  referencia_tipo: string | null;
  referencia_id: number | null;
};

export type CostosLote = {
  lote_id: number;
  codigo: string;
  estanque_id: number;
  alevinos: string | number;
  alimento: string | number;
  biofloc_insumos: string | number;
  otros_costos_directos: string | number;
  costo_directo_lote: string | number;
  costos_estanque_no_asignados: string | number;
  kg_alimento_suministrado: string | number;
  peces_sembrados: number;
  costo_por_pez: string | number | null;
  kg_cosechados: string | number;
  costo_por_kg: string | number | null;
  ventas: string | number;
  kg_vendidos: string | number;
  costo_ventas_estimado: string | number;
  utilidad_bruta_estimada: string | number | null;
  margen_bruto_estimado_pct: string | number | null;
  detalle: CostoLoteDetalle[];
};
