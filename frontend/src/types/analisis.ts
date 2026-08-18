export type AnalisisPendientes = Record<string, string>;

/** Decimal del API: llega como string para no perder precisión. */
export type ApiDecimal = string | number;

export type AnalisisStats = {
  unidad: string | null;
  n: number;
  primero: ApiDecimal | null;
  ultimo: ApiDecimal | null;
  promedio: ApiDecimal | null;
  minimo: ApiDecimal | null;
  maximo: ApiDecimal | null;
  mediana: ApiDecimal | null;
  variacion_porcentual: ApiDecimal | null;
  variacion_motivo: string | null;
};

export type AnalisisComparacion = {
  real: ApiDecimal | null;
  objetivo: ApiDecimal | null;
  unidad: string | null;
  diferencia: ApiDecimal | null;
  diferencia_porcentaje: ApiDecimal | null;
  motivo: string | null;
};

export type EstadoAnalitico = "NORMAL" | "ALERTA" | "CRITICO" | "SIN_REFERENCIA" | "SIN_DATOS";

export type CumplimientoRango = "DENTRO_RANGO" | "FUERA_RANGO" | "NO_EVALUABLE";

export type EvaluacionIndicador = {
  indicador: string;
  etiqueta: string;
  real: ApiDecimal | null;
  objetivo: ApiDecimal | null;
  minimo: ApiDecimal | null;
  maximo: ApiDecimal | null;
  unidad: string | null;
  diferencia_objetivo: ApiDecimal | null;
  diferencia_objetivo_porcentaje: ApiDecimal | null;
  desviacion_rango: ApiDecimal | null;
  desviacion_rango_porcentaje: ApiDecimal | null;
  estado_analitico: EstadoAnalitico | null;
  cumplimiento_rango: CumplimientoRango;
  motivo: string | null;
  explicacion: string;
  referencia: string | null;
  fecha_real: string | null;
  fecha_referencia: string | null;
};

export type RecomendacionAnalitica = {
  indicador: string;
  estado_analitico: EstadoAnalitico | null;
  cumplimiento_rango: CumplimientoRango;
  motivo: string;
  recomendacion: string;
};

export type AnalisisIndicadores = {
  peces_sembrados: number;
  mortalidad_acumulada: number;
  peces_cosechados: number;
  poblacion_estimada: number;
  supervivencia_porcentaje: ApiDecimal | null;
  mortalidad_porcentaje: ApiDecimal | null;
  ultima_biometria_id: number | null;
  peso_promedio_g: ApiDecimal | null;
  fecha_ultima_biometria: string | null;
  peso_inicial_g: ApiDecimal | null;
  dias_cultivo: number;
  semana_cultivo: number;
  ganancia_peso_g: ApiDecimal | null;
  ganancia_diaria_g: ApiDecimal | null;
  biomasa_inicial_kg: ApiDecimal | null;
  biomasa_actual_kg: ApiDecimal | null;
  alimento_real_acumulado_kg: ApiDecimal | null;
  fca: ApiDecimal | null;
  fca_disponible: boolean;
  fca_motivo: string | null;
  racion_diaria_recomendada_kg: ApiDecimal | null;
  numero_raciones_diarias: number | null;
};

export type AnalisisReferenciaProduccion = {
  id: number;
  especie_id: number;
  etapa_productiva_id: number;
  semana_desde: number;
  semana_hasta: number;
  peso_esperado_g: ApiDecimal | null;
  tasa_alimentacion_pct: ApiDecimal | null;
  observaciones: string | null;
  activo: boolean;
};

export type AnalisisReferenciaSemana = {
  semana_cultivo: number;
  referencia_id: number | null;
  peso_esperado_g: ApiDecimal | null;
  tasa_alimentacion_pct: ApiDecimal | null;
  motivo: string | null;
};

export type AnalisisBiometria = {
  id: number;
  fecha_hora: string;
  cantidad_muestra: number;
  peso_total_muestra_g: ApiDecimal;
  peso_promedio_g: ApiDecimal | null;
  semana_cultivo: number;
  referencia_id: number | null;
  peso_esperado_g: ApiDecimal | null;
  diferencia_peso_g: ApiDecimal | null;
  diferencia_peso_pct: ApiDecimal | null;
};

export type AnalisisMortalidad = {
  id: number;
  fecha_hora: string;
  cantidad: number;
  acumulada: number;
  mortalidad_porcentaje: ApiDecimal | null;
};

export type AnalisisPoblacionPunto = {
  fecha_hora: string;
  evento: string;
  mortalidad_acumulada: number;
  peces_cosechados: number;
  poblacion_estimada: number;
  mortalidad_porcentaje: ApiDecimal | null;
  supervivencia_porcentaje: ApiDecimal | null;
};

export type AnalisisBiomasaPunto = {
  fecha_hora: string;
  biometria_id: number;
  poblacion_estimada: number;
  peso_promedio_g: ApiDecimal;
  biomasa_kg: ApiDecimal;
  ganancia_biomasa_kg: ApiDecimal | null;
};

export type AnalisisFcaPunto = {
  fecha_hora: string;
  biometria_id: number;
  alimento_real_acumulado_kg: ApiDecimal | null;
  biomasa_kg: ApiDecimal;
  ganancia_biomasa_kg: ApiDecimal | null;
  fca: ApiDecimal | null;
  fca_disponible: boolean;
  fca_motivo: string | null;
};

export type AnalisisCrecimientoPunto = {
  fecha_hora: string;
  biometria_id: number;
  dias_cultivo: number;
  peso_promedio_g: ApiDecimal;
  ganancia_peso_g: ApiDecimal | null;
  ganancia_diaria_g: ApiDecimal | null;
  motivo: string | null;
};

export type ProductividadLote = {
  biomasa_actual_kg: ApiDecimal | null;
  ganancia_biomasa_kg: ApiDecimal | null;
  peso_cosechado_kg: ApiDecimal;
  peces_cosechados: number;
  ganancia_peso_g: ApiDecimal | null;
  ganancia_diaria_g: ApiDecimal | null;
  supervivencia_porcentaje: ApiDecimal | null;
  mortalidad_porcentaje: ApiDecimal | null;
  motivos: Record<string, string>;
};

export type EficienciaLote = {
  fca: ApiDecimal | null;
  fca_disponible: boolean;
  fca_motivo: string | null;
  alimento_real_acumulado_kg: ApiDecimal | null;
  ganancia_biomasa_kg: ApiDecimal | null;
  desviacion_peso_porcentaje: ApiDecimal | null;
  supervivencia_porcentaje: ApiDecimal | null;
  mortalidad_porcentaje: ApiDecimal | null;
  costo_por_kg: ApiDecimal | null;
  costo_por_kg_motivo: string;
  costo_alimentacion: ApiDecimal | null;
  costo_alimentacion_motivo: string;
};

export type FinanzasLote = {
  ingresos_lote: ApiDecimal;
  ventas_registradas: number;
  gastos_directos_lote: ApiDecimal;
  gastos_registrados: number;
  costos_completos: boolean;
  costos_completos_motivo: string;
  utilidad: ApiDecimal | null;
  utilidad_motivo: string;
  margen_porcentaje: ApiDecimal | null;
  margen_motivo: string;
};

export type AnalisisAguaMedicion = {
  id: number;
  parametro_id: number;
  parametro: string;
  unidad: string;
  valor: ApiDecimal;
  fecha_hora: string;
  valor_minimo: ApiDecimal | null;
  valor_maximo: ApiDecimal | null;
  fuera_de_rango: boolean | null;
};

export type AnalisisAguaEstadisticas = {
  parametro_id: number;
  parametro: string;
  unidad: string;
  valor_minimo: ApiDecimal | null;
  valor_maximo: ApiDecimal | null;
  con_referencia: boolean;
  fuera_de_rango_n: number | null;
  fuera_de_rango_porcentaje: ApiDecimal | null;
  estadisticas: AnalisisStats;
};

export type AnalisisBioflocMedicion = {
  id: number;
  fecha_hora: string;
  volumen_sedimentable: ApiDecimal;
  unidad: string;
  relacion_cn: ApiDecimal | null;
};

export type AnalisisAlimentoRegistro = {
  id: number;
  fecha_hora: string;
  producto_id: number;
  producto_codigo: string;
  producto_nombre: string;
  unidad: string;
  cantidad: ApiDecimal;
  cantidad_kg: ApiDecimal | null;
  acumulado_kg: ApiDecimal | null;
  convertible_a_kg: boolean;
};

export type AnalisisEstadisticas = {
  peso_promedio_g: AnalisisStats;
  biomasa_kg: AnalisisStats;
  poblacion_estimada: AnalisisStats;
  supervivencia_porcentaje: AnalisisStats;
  mortalidad_acumulada: AnalisisStats;
  alimento_acumulado_kg: AnalisisStats;
  fca: AnalisisStats;
  volumen_sedimentable: AnalisisStats;
  relacion_cn: AnalisisStats;
  agua: AnalisisAguaEstadisticas[];
};

export type AnalisisDefiniciones = {
  zona_horaria: string;
  dias_cultivo: string;
  semana_cultivo: string;
  unidad_masa_productiva: string;
  biomasa_inicial_kg: string;
  biomasa_actual_kg: string;
  ganancia_peso_g: string;
  ganancia_diaria_g: string;
  alimento_real_acumulado_kg: string;
  fca: string;
  referencia_produccion: string;
  racion_diaria_recomendada_kg: string;
  numero_raciones_diarias: string;
  poblacion_as_of: string;
  serie_biomasa: string;
  serie_fca: string;
  alimento_convertible_kg: string;
  estadisticas: string;
  mediana: string;
  variacion_porcentual: string;
  comparacion_real_objetivo: string;
  filtros_fecha: string;
  estado_analitico: string;
  cumplimiento_rango: string;
  recomendaciones: string;
};

export type AnalisisLote = {
  lote: {
    id: number;
    codigo: string;
    fecha_siembra: string;
    fecha_cierre: string | null;
    cantidad_sembrada: number;
    peso_inicial_promedio_g: ApiDecimal | null;
    estado: { id: number; nombre: string; descripcion: string | null };
  };
  estanque: { id: number; codigo: string; nombre: string };
  especie: { id: number; nombre_comun: string; nombre_cientifico: string | null };
  etapa: { id: number; nombre: string; orden: number };
  definiciones: AnalisisDefiniciones;
  filtros: { fecha_desde: string | null; fecha_hasta: string | null; nota: string };
  indicadores: AnalisisIndicadores;
  pendientes: AnalisisPendientes;
  referencia_produccion: AnalisisReferenciaProduccion | null;
  referencias_por_semana: AnalisisReferenciaSemana[];
  comparaciones: { peso_g: AnalisisComparacion };
  evaluaciones: EvaluacionIndicador[];
  recomendaciones: RecomendacionAnalitica[];
  productividad: ProductividadLote;
  eficiencia: EficienciaLote;
  finanzas: FinanzasLote;
  estadisticas: AnalisisEstadisticas;
  biometrias: AnalisisBiometria[];
  mortalidades: AnalisisMortalidad[];
  serie_poblacion: AnalisisPoblacionPunto[];
  serie_biomasa: AnalisisBiomasaPunto[];
  serie_crecimiento: AnalisisCrecimientoPunto[];
  serie_fca: AnalisisFcaPunto[];
  agua: AnalisisAguaMedicion[];
  agua_serie: AnalisisAguaMedicion[];
  biofloc: AnalisisBioflocMedicion | null;
  biofloc_serie: AnalisisBioflocMedicion[];
  alimentacion_real_por_unidad: Array<{ unidad: string; cantidad: ApiDecimal }>;
  alimentacion_real: AnalisisAlimentoRegistro[];
};

export type EstanqueComparativo = {
  estanque_id: number;
  codigo: string;
  nombre: string;
  activo: boolean;
  lote_id: number | null;
  lote_codigo: string | null;
  especie: string | null;
  etapa: string | null;
  fecha_siembra: string | null;
  dias_cultivo: number | null;
  semana_cultivo: number | null;
  peces_sembrados: number | null;
  poblacion_estimada: number | null;
  peso_promedio_g: ApiDecimal | null;
  biomasa_actual_kg: ApiDecimal | null;
  supervivencia_porcentaje: ApiDecimal | null;
  mortalidad_porcentaje: ApiDecimal | null;
  fca: ApiDecimal | null;
  fca_disponible: boolean;
  fca_motivo: string | null;
  agua_parametros_medidos: number;
  agua_parametros_con_referencia: number;
  agua_parametros_fuera_de_rango: number | null;
  ganancia_peso_g: ApiDecimal | null;
  alimento_real_acumulado_kg: ApiDecimal | null;
  productividad: ProductividadLote | null;
  eficiencia: EficienciaLote | null;
  finanzas: FinanzasLote | null;
  estado_biofloc: EstadoAnalitico;
  sin_lote_activo_motivo: string | null;
};

export type ResumenGranja = {
  estanques: number;
  estanques_con_lote_activo: number;
  peces_sembrados: number;
  poblacion_estimada: number;
  mortalidad_acumulada: number;
  biomasa_actual_kg: ApiDecimal | null;
  lotes_sin_biomasa: number;
  supervivencia_porcentaje: ApiDecimal | null;
  mortalidad_porcentaje: ApiDecimal | null;
  lotes_con_fca: number;
  fca: ApiDecimal | null;
  fca_motivo: string;
  peso_cosechado_kg: ApiDecimal;
  peces_cosechados: number;
  ingresos_lotes_activos: ApiDecimal;
  gastos_directos_lotes_activos: ApiDecimal;
  utilidad: ApiDecimal | null;
  utilidad_motivo: string;
};

export type CicloComparativo = {
  lote_id: number;
  lote_codigo: string;
  estanque_id: number;
  estanque_codigo: string;
  especie: string;
  etapa: string;
  estado_lote: string;
  fecha_siembra: string;
  fecha_cierre: string | null;
  dias_cultivo: number;
  semana_cultivo: number;
  productividad: ProductividadLote;
  eficiencia: EficienciaLote;
  finanzas: FinanzasLote;
};

export type ComparativoEstanques = {
  definiciones: Record<string, string>;
  resumen: ResumenGranja;
  estanques: EstanqueComparativo[];
  ciclos: CicloComparativo[];
};
