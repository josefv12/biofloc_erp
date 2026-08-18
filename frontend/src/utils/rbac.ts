import type { RolNombre } from "../types/auth";

const ROLES: readonly RolNombre[] = ["ADMINISTRADOR", "TECNICO", "OPERARIO"];

export function isRolNombre(value: string | undefined): value is RolNombre {
  return Boolean(value && (ROLES as readonly string[]).includes(value));
}

export function hasRole(userRol: string | undefined, role: RolNombre): boolean {
  return userRol === role;
}

export function hasAnyRole(userRol: string | undefined, roles: readonly RolNombre[]): boolean {
  return Boolean(userRol && roles.includes(userRol as RolNombre));
}

/** Acciones alineadas al RBAC real del backend. La UI solo oculta; el servidor valida. */
export const actions = {
  crearEstanque: ["ADMINISTRADOR"],
  editarEstanque: ["ADMINISTRADOR", "TECNICO"],
  crearLote: ["ADMINISTRADOR", "TECNICO"],
  editarLote: ["ADMINISTRADOR", "TECNICO"],
  crearBiometria: ["ADMINISTRADOR", "TECNICO"],
  crearMortalidad: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  crearCosecha: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarAgua: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarBiofloc: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarAlimentacion: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  escribirCatalogo: ["ADMINISTRADOR", "TECNICO"],
  escribirEquipo: ["ADMINISTRADOR", "TECNICO"],
  registrarMantenimiento: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarFalla: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  actualizarFalla: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarEventoEnergia: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  actualizarEventoEnergia: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarAlarma: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  actualizarAlarma: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  escribirProducto: ["ADMINISTRADOR", "TECNICO"],
  registrarMovimiento: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarCompra: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarGasto: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  registrarVenta: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
  verCatalogos: ["ADMINISTRADOR", "TECNICO", "OPERARIO"],
} as const;

export type Accion = keyof typeof actions;

export function can(userRol: string | undefined, action: Accion): boolean {
  return hasAnyRole(userRol, actions[action]);
}
