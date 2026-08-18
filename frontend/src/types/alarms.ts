export type TipoAlarma = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type NivelAlarma = {
  id: number;
  nombre: string;
  prioridad: number;
};

export type EstadoAlarma = {
  id: number;
  nombre: string;
  descripcion: string | null;
};

export type Alarma = {
  id: number;
  tipo_alarma_id: number;
  nivel_alarma_id: number;
  estado_alarma_id: number;
  lote_id: number | null;
  equipo_id: number | null;
  evento_energia_id: number | null;
  fecha_hora: string;
  titulo: string;
  mensaje: string;
  atendida_por: number | null;
  fecha_atencion: string | null;
  observaciones: string | null;
  created_at: string;
  tipo: TipoAlarma;
  nivel: NivelAlarma;
  estado: EstadoAlarma;
};

export type AlarmaCreate = {
  tipo_alarma_id: number;
  nivel_alarma_id: number;
  estado_alarma_id?: number | null;
  lote_id?: number | null;
  equipo_id?: number | null;
  evento_energia_id?: number | null;
  fecha_hora?: string | null;
  titulo: string;
  mensaje: string;
  observaciones?: string | null;
};

export type AlarmaUpdate = {
  estado_alarma_id?: number | null;
  observaciones?: string | null;
};
