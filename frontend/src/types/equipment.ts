export type TipoEquipo = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type EstadoEquipo = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type Equipo = {
  id: number;
  codigo: string;
  nombre: string;
  tipo_equipo_id: number;
  estado_id: number;
  marca: string | null;
  modelo: string | null;
  numero_serie: string | null;
  fecha_adquisicion: string | null;
  valor_adquisicion: string | number | null;
  ubicacion: string | null;
  observaciones: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
  tipo: TipoEquipo;
  estado: EstadoEquipo;
};

export type EquipoCreate = {
  codigo: string;
  nombre: string;
  tipo_equipo_id: number;
  estado_id: number;
  marca?: string | null;
  modelo?: string | null;
  numero_serie?: string | null;
  fecha_adquisicion?: string | null;
  valor_adquisicion?: number | null;
  ubicacion?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type EquipoUpdate = {
  codigo?: string;
  nombre?: string;
  tipo_equipo_id?: number;
  estado_id?: number;
  marca?: string | null;
  modelo?: string | null;
  numero_serie?: string | null;
  fecha_adquisicion?: string | null;
  valor_adquisicion?: number | null;
  ubicacion?: string | null;
  observaciones?: string | null;
  activo?: boolean;
};

export type TipoMantenimiento = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type Mantenimiento = {
  id: number;
  equipo_id: number;
  tipo_mantenimiento_id: number;
  fecha: string;
  descripcion: string;
  costo: string | number;
  proveedor: string | null;
  observaciones: string | null;
  registrado_por: number;
  created_at: string;
};

export type MantenimientoCreate = {
  equipo_id: number;
  tipo_mantenimiento_id: number;
  fecha: string;
  descripcion: string;
  costo?: number;
  proveedor?: string | null;
  observaciones?: string | null;
};

export type Falla = {
  id: number;
  equipo_id: number;
  fecha_hora: string;
  descripcion: string;
  impacto: string | null;
  solucion: string | null;
  costo: string | number;
  registrada_por: number;
  created_at: string;
};

export type FallaCreate = {
  equipo_id: number;
  fecha_hora: string;
  descripcion: string;
  impacto?: string | null;
  solucion?: string | null;
  costo?: number;
};

export type FallaUpdate = {
  descripcion?: string;
  impacto?: string | null;
  solucion?: string | null;
  costo?: number;
};

export type EventoEnergia = {
  id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string | null;
  duracion_minutos: number | null;
  tipo: string;
  respaldo_activado: boolean;
  equipo_respaldo_id: number | null;
  observaciones: string | null;
  registrado_por: number | null;
  created_at: string;
};

export type EventoEnergiaCreate = {
  fecha_hora_inicio: string;
  fecha_hora_fin?: string | null;
  tipo?: string;
  respaldo_activado?: boolean;
  equipo_respaldo_id?: number | null;
  observaciones?: string | null;
};

export type EventoEnergiaUpdate = {
  fecha_hora_fin?: string | null;
  tipo?: string;
  respaldo_activado?: boolean;
  equipo_respaldo_id?: number | null;
  observaciones?: string | null;
};
