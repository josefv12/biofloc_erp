export type RolNombre = "ADMINISTRADOR" | "TECNICO" | "OPERARIO";

export type LoginRequest = {
  correo: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UsuarioActual = {
  id: number;
  nombre: string;
  correo: string;
  rol: string;
  activo: boolean;
};

export type RolCatalogo = {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type UsuarioGestion = {
  id: number;
  nombre: string;
  correo: string;
  rol_id: number;
  rol: string;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type UsuarioCreate = {
  nombre: string;
  correo: string;
  password: string;
  rol_id: number;
  activo?: boolean;
};

export type UsuarioUpdate = {
  nombre?: string;
  correo?: string;
  password?: string;
  rol_id?: number;
  activo?: boolean;
};

export type AuthState = {
  token: string | null;
  user: UsuarioActual | null;
  loading: boolean;
};
