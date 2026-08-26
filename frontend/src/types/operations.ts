export type ParametroAgua = {
  id: number;
  nombre: string;
  unidad: string;
  descripcion: string | null;
  activo: boolean;
};

export type ReferenciaAgua = {
  id: number;
  especie_id: number;
  etapa_productiva_id: number;
  parametro_id: number;
  valor_minimo: string | number | null;
  valor_maximo: string | number | null;
  observaciones: string | null;
  activo: boolean;
};

export type IndicadorBiofloc = "VOLUMEN_SEDIMENTABLE" | "RELACION_CN";

export type ReferenciaBiofloc = {
  id: number;
  especie_id: number;
  etapa_productiva_id: number;
  indicador: IndicadorBiofloc;
  valor_minimo: string | number | null;
  valor_objetivo: string | number | null;
  valor_maximo: string | number | null;
  unidad: string | null;
  observaciones: string | null;
  activo: boolean;
};

export type ReferenciaBioflocCreate = {
  especie_id: number;
  etapa_productiva_id: number;
  indicador: IndicadorBiofloc;
  valor_minimo?: number | null;
  valor_objetivo?: number | null;
  valor_maximo?: number | null;
  unidad?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type ReferenciaBioflocUpdate = {
  valor_minimo?: number | null;
  valor_objetivo?: number | null;
  valor_maximo?: number | null;
  unidad?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type MedicionAgua = {
  id: number;
  lote_id: number;
  parametro_id: number;
  fecha_hora: string;
  valor: string | number;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
};

export type MedicionAguaCreate = {
  lote_id: number;
  parametro_id: number;
  fecha_hora: string;
  valor: number;
  observaciones?: string | null;
};

export type TipoAplicacionBiofloc = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type MedicionBiofloc = {
  id: number;
  lote_id: number;
  fecha_hora: string;
  volumen_sedimentable: string | number;
  unidad: string;
  observaciones: string | null;
  relacion_cn: string | number | null;
  registrado_por: number;
  created_at: string;
};

export type MedicionBioflocCreate = {
  lote_id: number;
  fecha_hora: string;
  volumen_sedimentable: number;
  unidad?: string;
  observaciones?: string | null;
  relacion_cn?: number | null;
};

export type AplicacionBiofloc = {
  id: number;
  lote_id: number;
  tipo_aplicacion_id: number;
  producto_id: number | null;
  fecha_hora: string;
  cantidad: string | number | null;
  unidad: string | null;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
  stock_restante?: number | null;
};

export type AplicacionBioflocCreate = {
  lote_id: number;
  tipo_aplicacion_id: number;
  producto_id?: number | null;
  fecha_hora: string;
  cantidad?: number | null;
  unidad?: string | null;
  observaciones?: string | null;
};

export type Alimentacion = {
  id: number;
  lote_id: number;
  producto_id: number;
  fecha_hora: string;
  cantidad: number;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
  stock_restante?: number | null;
};

export type AlimentacionCreate = {
  lote_id: number;
  producto_id: number;
  fecha_hora: string;
  cantidad: number;
  observaciones?: string | null;
};

export type Producto = {
  id: number;
  codigo: string;
  nombre: string;
  categoria_id: number;
  unidad_id: number;
  stock_minimo: string | number;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Unidad = {
  id: number;
  nombre: string;
  simbolo: string;
  activo: boolean;
};
