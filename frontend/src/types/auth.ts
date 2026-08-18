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

export type AuthState = {
  token: string | null;
  user: UsuarioActual | null;
  loading: boolean;
};
