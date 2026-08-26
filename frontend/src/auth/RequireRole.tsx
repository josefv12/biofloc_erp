import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { hasAnyRole } from "../utils/rbac";
import type { RolNombre } from "../types/auth";

export function RequireRole({ roles, children }: { roles: readonly RolNombre[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!hasAnyRole(user?.rol, roles)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
