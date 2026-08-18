import { useAuth } from "../auth/AuthProvider";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";

export function PerfilPage() {
  const { user, logout } = useAuth();

  return (
    <div>
      <PageHeader title="Mi perfil" description="Datos de la sesión actual. No hay edición de usuario en esta versión." />

      <div className="max-w-lg rounded-xl border border-[var(--bf-border)] bg-white p-5">
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-[var(--bf-muted)]">Nombre</dt>
            <dd className="mt-0.5 font-medium text-[var(--bf-ink)]">{user?.nombre}</dd>
          </div>
          <div>
            <dt className="text-[var(--bf-muted)]">Correo</dt>
            <dd className="mt-0.5 text-[var(--bf-ink)]">{user?.correo}</dd>
          </div>
          <div>
            <dt className="text-[var(--bf-muted)]">Rol</dt>
            <dd className="mt-1">
              <StatusBadge label={user?.rol ?? "—"} tone="info" />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--bf-muted)]">Estado</dt>
            <dd className="mt-1">
              <StatusBadge label={user?.activo ? "Activo" : "Inactivo"} tone={user?.activo ? "ok" : "danger"} />
            </dd>
          </div>
        </dl>

        <button type="button" className="bf-btn-secondary mt-6" onClick={logout}>
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
