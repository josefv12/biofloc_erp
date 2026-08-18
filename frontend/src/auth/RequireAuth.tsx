import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { LoadingState } from "../components/LoadingState";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, token } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bf-bg)]">
        <LoadingState label="Verificando sesión…" />
      </div>
    );
  }

  if (!token || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  return children;
}
