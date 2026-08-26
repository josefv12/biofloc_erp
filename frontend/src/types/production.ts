export type EstadoEstanque = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type Estanque = {
  id: number;
  codigo: string;
  nombre: string;
  diametro: number;
  profundidad: number;
  estado_id: number;
  estado: EstadoEstanque;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type EstanqueCreate = {
  codigo: string;
  nombre: string;
  diametro: number;
  profundidad: number;
  estado_id: number;
  activo?: boolean;
};

export type EstanqueUpdate = {
  nombre?: string;
  diametro?: number;
  profundidad?: number;
  estado_id?: number;
  activo?: boolean;
};

export type Especie = {
  id: number;
  nombre_comun: string;
  nombre_cientifico: string | null;
};

export type EspecieCatalogo = Especie & {
  activo: boolean;
  n_referencias_produccion: number;
  n_referencias_agua: number;
};

export type EspecieCreate = {
  nombre_comun: string;
  nombre_cientifico?: string | null;
  activo?: boolean;
};

export type EspecieUpdate = {
  nombre_comun?: string;
  nombre_cientifico?: string | null;
  activo?: boolean;
};

export type EtapaProductiva = {
  id: number;
  nombre: string;
  orden: number;
};

export type EtapaProductivaCatalogo = EtapaProductiva & {
  descripcion: string | null;
  activo: boolean;
};

export type EstadoLote = {
  id: number;
  nombre: string;
  descripcion: string | null;
};

export type EstadoLoteCatalogo = EstadoLote & {
  activo: boolean;
};

export type ReferenciaProduccion = {
  id: number;
  especie_id: number;
  etapa_productiva_id: number;
  semana_desde: number;
  semana_hasta: number;
  peso_esperado_g: string | number | null;
  tasa_alimentacion_pct: string | number | null;
  raciones_min: number | null;
  raciones_max: number | null;
  fase: string | null;
  observaciones: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type ReferenciaProduccionCreate = {
  especie_id: number;
  etapa_productiva_id: number;
  semana_desde: number;
  semana_hasta: number;
  peso_esperado_g?: number | null;
  tasa_alimentacion_pct?: number | null;
  raciones_min?: number | null;
  raciones_max?: number | null;
  fase?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type ReferenciaProduccionUpdate = {
  especie_id?: number;
  etapa_productiva_id?: number;
  semana_desde?: number;
  semana_hasta?: number;
  peso_esperado_g?: number | null;
  tasa_alimentacion_pct?: number | null;
  raciones_min?: number | null;
  raciones_max?: number | null;
  fase?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type Lote = {
  id: number;
  codigo: string;
  estanque_id: number;
  especie_id: number;
  etapa_productiva_id: number;
  estado_id: number;
  fecha_siembra: string;
  fecha_cierre: string | null;
  cantidad_sembrada: number;
  peso_inicial_promedio_g: number | null;
  observaciones: string | null;
  created_at: string;
  updated_at: string;
  especie: Especie;
  etapa_productiva: EtapaProductiva;
  estado: EstadoLote;
};

export type LoteCreate = {
  codigo: string;
  estanque_id: number;
  especie_id: number;
  etapa_productiva_id: number;
  estado_id: number;
  fecha_siembra: string;
  fecha_cierre?: string | null;
  cantidad_sembrada: number;
  peso_inicial_promedio_g?: number | null;
  observaciones?: string | null;
};

export type LoteUpdate = {
  etapa_productiva_id?: number;
  estado_id?: number;
  fecha_cierre?: string | null;
  observaciones?: string | null;
};

export type Biometria = {
  id: number;
  lote_id: number;
  fecha_hora: string;
  cantidad_muestra: number;
  peso_total_muestra_g: number;
  observaciones: string | null;
  registrado_por: number;
  talla_promedio: number | null;
  unidad_talla: string | null;
  created_at: string;
};

export type BiometriaCreate = {
  lote_id: number;
  fecha_hora: string;
  cantidad_muestra: number;
  peso_total_muestra_g: number;
  observaciones?: string | null;
  talla_promedio?: number | null;
  unidad_talla?: string | null;
};

export type Mortalidad = {
  id: number;
  lote_id: number;
  fecha_hora: string;
  cantidad: number;
  causa: string | null;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
};

export type MortalidadCreate = {
  lote_id: number;
  fecha_hora: string;
  cantidad: number;
  causa?: string | null;
  observaciones?: string | null;
};

export type Cosecha = {
  id: number;
  lote_id: number;
  fecha_hora: string;
  cantidad_peces: number;
  peso_total_kg: string | number;
  peso_promedio_g: string | number | null;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
};

export type CosechaCreate = {
  lote_id: number;
  fecha_hora: string;
  cantidad_peces: number;
  peso_total_kg: number;
  peso_promedio_g?: number | null;
  observaciones?: string | null;
};
