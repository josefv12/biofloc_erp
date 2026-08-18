import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useAuth } from "../auth/AuthProvider";
import { returnToPath } from "../auth/returnTo";
import { ErrorAlert } from "../components/ErrorAlert";
import { LoadingState } from "../components/LoadingState";
import { apiErrorMessage } from "../utils/apiError";

type FormValues = {
  correo: string;
  password: string;
};

export function LoginPage() {
  const { login, user, loading } = useAuth();
  const location = useLocation();
  const destino = returnToPath((location.state as { from?: unknown } | null)?.from);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>({
    defaultValues: { correo: "", password: "" },
  });

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bf-bg)]">
        <LoadingState label="Cargando…" />
      </div>
    );
  }

  if (user) {
    return <Navigate to={destino} replace />;
  }

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      await login(values.correo.trim(), values.password, destino);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div className="flex min-h-screen bg-[var(--bf-bg)]">
      <div className="relative hidden w-[42%] flex-col justify-between bg-[var(--bf-sidebar)] p-10 text-white lg:flex">
        <p className="text-sm font-medium tracking-wide text-white/70">BIOFLOC ERP V1</p>
        <div>
          <h1 className="font-display text-4xl font-semibold leading-tight">
            Gestión de la
            <br />
            piscicultura
          </h1>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/70">
            Registro de producción, agua, inventario y operación para el proyecto de tilapia en
            sistema Biofloc.
          </p>
        </div>
        <p className="text-xs text-white/40">Fondo Emprender · uso interno de la granja</p>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[var(--bf-border)] bg-white p-8 shadow-[0_12px_40px_rgba(22,51,45,0.06)]">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--bf-accent)]">
            Ingreso
          </p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-[var(--bf-ink)]">
            Iniciar sesión
          </h2>
          <p className="mt-2 text-sm text-[var(--bf-muted)]">
            Use el correo y la contraseña asignados a su rol.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            {error ? <ErrorAlert message={error} /> : null}

            <label className="block text-sm">
              <span className="mb-1 block font-medium text-[var(--bf-ink)]">Correo</span>
              <input
                type="email"
                autoComplete="username"
                className="bf-input"
                {...register("correo", { required: true })}
              />
            </label>

            <label className="block text-sm">
              <span className="mb-1 block font-medium text-[var(--bf-ink)]">Contraseña</span>
              <input
                type="password"
                autoComplete="current-password"
                className="bf-input"
                {...register("password", { required: true })}
              />
            </label>

            <button type="submit" className="bf-btn-primary w-full justify-center" disabled={isSubmitting}>
              {isSubmitting ? "Ingresando…" : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
