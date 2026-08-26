import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { createUsuario, listRoles, listUsuarios, updateUsuario } from "../../api/users";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDateTime } from "../../utils/format";
import type { UsuarioGestion } from "../../types/auth";

type UsuarioForm = {
  nombre: string;
  correo: string;
  password: string;
  confirmar: string;
  rol_id: string;
  activo: "true" | "false";
};

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return `${partes[0][0]}${partes[1][0]}`.toUpperCase();
}

function tonoRol(rol: string): "info" | "ok" | "neutral" {
  if (rol === "ADMINISTRADOR") return "info";
  if (rol === "TECNICO") return "ok";
  return "neutral";
}

export function UsuariosPage() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<UsuarioGestion | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<UsuarioForm>();

  const usuariosQuery = useQuery({ queryKey: ["usuarios"], queryFn: () => listUsuarios(false) });
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: () => listRoles(true) });

  const resumen = useMemo(() => {
    const filas = usuariosQuery.data ?? [];
    return {
      activos: filas.filter((row) => row.activo).length,
      administradores: filas.filter((row) => row.rol === "ADMINISTRADOR" && row.activo).length,
      tecnicos: filas.filter((row) => row.rol === "TECNICO" && row.activo).length,
      inactivos: filas.filter((row) => !row.activo).length,
    };
  }, [usuariosQuery.data]);

  const createMut = useMutation({
    mutationFn: createUsuario,
    onSuccess: async () => {
      setCreating(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["usuarios"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateUsuario>[1] }) =>
      updateUsuario(id, data),
    onSuccess: async () => {
      setEditing(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["usuarios"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      nombre: "",
      correo: "",
      password: "",
      confirmar: "",
      rol_id: "",
      activo: "true",
    });
    setCreating(true);
  }

  function openEdit(row: UsuarioGestion) {
    setFormError(null);
    form.reset({
      nombre: row.nombre,
      correo: row.correo,
      password: "",
      confirmar: "",
      rol_id: String(row.rol_id),
      activo: row.activo ? "true" : "false",
    });
    setEditing(row);
  }

  function onCreate(values: UsuarioForm) {
    setFormError(null);
    if (!values.rol_id) {
      setFormError("Seleccione un rol del catálogo.");
      return;
    }
    if (values.password !== values.confirmar) {
      setFormError("La confirmación de contraseña no coincide.");
      return;
    }
    createMut.mutate({
      nombre: values.nombre.trim(),
      correo: values.correo.trim(),
      password: values.password,
      rol_id: Number(values.rol_id),
      activo: values.activo === "true",
    });
  }

  function onEdit(values: UsuarioForm) {
    if (!editing) return;
    setFormError(null);
    if (!values.rol_id) {
      setFormError("Seleccione un rol del catálogo.");
      return;
    }
    if (values.password || values.confirmar) {
      if (values.password !== values.confirmar) {
        setFormError("La confirmación de contraseña no coincide.");
        return;
      }
      if (values.password.length < 8) {
        setFormError("La contraseña debe tener al menos 8 caracteres.");
        return;
      }
    }
    updateMut.mutate({
      id: editing.id,
      data: {
        nombre: values.nombre.trim(),
        correo: values.correo.trim(),
        rol_id: Number(values.rol_id),
        activo: values.activo === "true",
        ...(values.password ? { password: values.password } : {}),
      },
    });
  }

  const pending = createMut.isPending || updateMut.isPending;
  const roles = rolesQuery.data ?? [];

  return (
    <div className="bf-enter">
      <PageHeader
        title="Usuarios"
        description="Administración de cuentas del ERP. Solo el administrador puede crear, editar o desactivar usuarios."
        actions={
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            + Nuevo usuario
          </button>
        }
      />

      {usuariosQuery.isLoading ? <LoadingState label="Cargando usuarios…" /> : null}
      {usuariosQuery.isError ? <ErrorAlert message={apiErrorMessage(usuariosQuery.error)} /> : null}

      {usuariosQuery.data ? (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Usuarios activos" value={String(resumen.activos)} />
            <KpiCard label="Administradores" value={String(resumen.administradores)} />
            <KpiCard label="Técnicos" value={String(resumen.tecnicos)} />
            <KpiCard label="Usuarios inactivos" value={String(resumen.inactivos)} />
          </div>

          <DataTable
            rows={usuariosQuery.data}
            rowKey={(row) => row.id}
            empty="Sin usuarios registrados."
            columns={[
              {
                key: "persona",
                header: "Usuario",
                render: (row) => (
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--bf-chip)] text-xs font-semibold text-[var(--bf-accent)]">
                      {iniciales(row.nombre)}
                    </span>
                    <span>
                      <span className="block font-medium">{row.nombre}</span>
                      <span className="block text-xs text-[var(--bf-muted)]">{row.correo}</span>
                    </span>
                  </div>
                ),
              },
              {
                key: "rol",
                header: "Rol",
                render: (row) => <StatusBadge label={row.rol} tone={tonoRol(row.rol)} />,
              },
              {
                key: "estado",
                header: "Estado",
                render: (row) => (
                  <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "danger"} />
                ),
              },
              {
                key: "alta",
                header: "Creado",
                render: (row) => formatDateTime(row.created_at),
              },
              {
                key: "acciones",
                header: "",
                className: "text-right",
                render: (row) => (
                  <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => openEdit(row)}>
                    Editar
                  </button>
                ),
              },
            ]}
          />
        </>
      ) : null}

      <Modal
        open={creating}
        title="Nuevo usuario"
        onClose={() => {
          setCreating(false);
          setFormError(null);
        }}
      >
        <UsuarioFormFields
          form={form}
          roles={roles}
          formError={formError}
          passwordRequired
          pending={pending}
          submitLabel="Crear usuario"
          onSubmit={onCreate}
        />
      </Modal>

      <Modal
        open={Boolean(editing)}
        title="Editar usuario"
        onClose={() => {
          setEditing(null);
          setFormError(null);
        }}
      >
        <UsuarioFormFields
          form={form}
          roles={roles}
          formError={formError}
          passwordRequired={false}
          pending={pending}
          submitLabel="Guardar cambios"
          onSubmit={onEdit}
        />
      </Modal>
    </div>
  );
}

function UsuarioFormFields({
  form,
  roles,
  formError,
  passwordRequired,
  pending,
  submitLabel,
  onSubmit,
}: {
  form: ReturnType<typeof useForm<UsuarioForm>>;
  roles: { id: number; nombre: string }[];
  formError: string | null;
  passwordRequired: boolean;
  pending: boolean;
  submitLabel: string;
  onSubmit: (values: UsuarioForm) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = form;

  return (
    <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
      {formError ? <ErrorAlert message={formError} /> : null}
      <Field label="Nombre" error={errors.nombre?.message}>
        <input
          className="bf-input"
          placeholder="Nombre completo"
          {...register("nombre", { required: "El nombre es obligatorio." })}
        />
      </Field>
      <Field label="Usuario / correo" error={errors.correo?.message}>
        <input
          className="bf-input"
          type="email"
          placeholder="correo@empresa.com"
          {...register("correo", { required: "El correo es obligatorio." })}
        />
      </Field>
      <Field
        label={passwordRequired ? "Contraseña inicial" : "Nueva contraseña (opcional)"}
        error={errors.password?.message}
      >
        <input
          className="bf-input"
          type="password"
          autoComplete="new-password"
          placeholder={passwordRequired ? "Mínimo 8 caracteres" : "Dejar vacío para no cambiar"}
          {...register("password", {
            required: passwordRequired ? "La contraseña es obligatoria." : false,
            minLength: passwordRequired
              ? { value: 8, message: "Mínimo 8 caracteres." }
              : undefined,
          })}
        />
      </Field>
      <Field label="Confirmar contraseña" error={errors.confirmar?.message}>
        <input
          className="bf-input"
          type="password"
          autoComplete="new-password"
          placeholder="Repita la contraseña"
          {...register("confirmar", {
            required: passwordRequired ? "Confirme la contraseña." : false,
          })}
        />
      </Field>
      <Field label="Rol" error={errors.rol_id?.message}>
        <select className="bf-input" {...register("rol_id", { required: "Seleccione un rol." })}>
          <option value="">Seleccione un rol</option>
          {roles.map((rol) => (
            <option key={rol.id} value={rol.id}>
              {rol.nombre}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Estado">
        <select className="bf-input" {...register("activo")}>
          <option value="true">Activo</option>
          <option value="false">Inactivo</option>
        </select>
      </Field>
      <div className="flex justify-end gap-2 pt-2">
        <button type="submit" className="bf-btn-primary" disabled={pending}>
          {pending ? "Guardando…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-[var(--bf-ink)]">{label}</span>
      {children}
      {error ? <span className="mt-1 block text-xs text-red-700">{error}</span> : null}
    </label>
  );
}
