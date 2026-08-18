import { useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import {
  createEquipo,
  listEquipos,
  listEstadosEquipo,
  listTiposEquipo,
  updateEquipo,
} from "../../api/equipment";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Equipo, EquipoCreate, EquipoUpdate } from "../../types/equipment";

type EquipoForm = {
  codigo: string;
  nombre: string;
  tipo_equipo_id: number;
  estado_id: number;
  marca: string;
  modelo: string;
  numero_serie: string;
  fecha_adquisicion: string;
  valor_adquisicion: string;
  ubicacion: string;
  observaciones: string;
  activo: boolean;
};

function toneEstado(nombre: string) {
  if (nombre === "OPERATIVO") return "ok" as const;
  if (nombre === "MANTENIMIENTO") return "warn" as const;
  if (nombre === "FUERA_DE_SERVICIO") return "danger" as const;
  return "neutral" as const;
}

export function EquiposPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const tipoId = Number(params.get("tipo_id") ?? "") || undefined;
  const estadoId = Number(params.get("estado_id") ?? "") || undefined;
  const codigo = params.get("codigo") ?? "";
  const incluirInactivos = params.get("inactivos") === "1";
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Equipo | null>(null);
  const [toToggle, setToToggle] = useState<Equipo | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeEscribir = can(user?.rol, "escribirEquipo");
  const form = useForm<EquipoForm>();

  const tiposQuery = useQuery({ queryKey: ["tipos-equipo"], queryFn: () => listTiposEquipo(false) });
  const estadosQuery = useQuery({ queryKey: ["estados-equipo"], queryFn: () => listEstadosEquipo(false) });
  const equiposQuery = useQuery({
    queryKey: ["equipos", tipoId, estadoId, codigo, incluirInactivos],
    queryFn: () =>
      listEquipos({
        soloActivos: !incluirInactivos,
        tipoEquipoId: tipoId,
        estadoId,
        codigo: codigo.trim() || undefined,
      }),
  });

  const createMut = useMutation({
    mutationFn: (data: EquipoCreate) => createEquipo(data),
    onSuccess: async () => {
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["equipos"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: EquipoUpdate }) => updateEquipo(id, data),
    onSuccess: async () => {
      setEditing(null);
      setToToggle(null);
      await queryClient.invalidateQueries({ queryKey: ["equipos"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function defaults(): EquipoForm {
    return {
      codigo: "",
      nombre: "",
      tipo_equipo_id: tiposQuery.data?.[0]?.id ?? 0,
      estado_id: estadosQuery.data?.find((row) => row.nombre === "OPERATIVO")?.id ?? estadosQuery.data?.[0]?.id ?? 0,
      marca: "",
      modelo: "",
      numero_serie: "",
      fecha_adquisicion: "",
      valor_adquisicion: "",
      ubicacion: "",
      observaciones: "",
      activo: true,
    };
  }

  function fromEquipo(row: Equipo): EquipoForm {
    return {
      codigo: row.codigo,
      nombre: row.nombre,
      tipo_equipo_id: row.tipo_equipo_id,
      estado_id: row.estado_id,
      marca: row.marca ?? "",
      modelo: row.modelo ?? "",
      numero_serie: row.numero_serie ?? "",
      fecha_adquisicion: row.fecha_adquisicion ?? "",
      valor_adquisicion: row.valor_adquisicion == null ? "" : String(row.valor_adquisicion),
      ubicacion: row.ubicacion ?? "",
      observaciones: row.observaciones ?? "",
      activo: row.activo,
    };
  }

  function toPayload(values: EquipoForm): EquipoCreate {
    const valor = values.valor_adquisicion.trim();
    return {
      codigo: values.codigo.trim(),
      nombre: values.nombre.trim(),
      tipo_equipo_id: Number(values.tipo_equipo_id),
      estado_id: Number(values.estado_id),
      marca: values.marca.trim() || null,
      modelo: values.modelo.trim() || null,
      numero_serie: values.numero_serie.trim() || null,
      fecha_adquisicion: values.fecha_adquisicion || null,
      valor_adquisicion: valor === "" ? null : Number(valor),
      ubicacion: values.ubicacion.trim() || null,
      observaciones: values.observaciones.trim() || null,
      activo: values.activo,
    };
  }

  return (
    <div>
      <PageHeader
        title="Equipos"
        description="Catálogo de equipos de la granja. Tipos y estados salen del API."
        actions={
          puedeEscribir ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset(defaults());
                setCreating(true);
              }}
            >
              Nuevo equipo
            </button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Código</span>
          <input
            className="bf-input"
            value={codigo}
            placeholder="Buscar código"
            onChange={(e) => setParam("codigo", e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Tipo</span>
          <select className="bf-input" value={tipoId ?? ""} onChange={(e) => setParam("tipo_id", e.target.value)}>
            <option value="">Todos</option>
            {(tiposQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Estado</span>
          <select className="bf-input" value={estadoId ?? ""} onChange={(e) => setParam("estado_id", e.target.value)}>
            <option value="">Todos</option>
            {(estadosQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-[var(--bf-muted)]">
          <input
            type="checkbox"
            checked={incluirInactivos}
            onChange={(e) => setParam("inactivos", e.target.checked ? "1" : "")}
          />
          Incluir inactivos
        </label>
      </div>

      {equiposQuery.isLoading ? <LoadingState /> : null}
      {equiposQuery.isError ? <ErrorAlert message={apiErrorMessage(equiposQuery.error)} /> : null}
      {equiposQuery.data ? (
        <DataTable
          rows={equiposQuery.data}
          rowKey={(row) => row.id}
          empty="No hay equipos."
          columns={[
            { key: "codigo", header: "Código", render: (row) => row.codigo },
            { key: "nombre", header: "Nombre", render: (row) => row.nombre },
            { key: "tipo", header: "Tipo", render: (row) => row.tipo.nombre },
            {
              key: "estado",
              header: "Estado",
              render: (row) => <StatusBadge label={row.estado.nombre} tone={toneEstado(row.estado.nombre)} />,
            },
            { key: "ubicacion", header: "Ubicación", render: (row) => row.ubicacion || "—" },
            {
              key: "valor",
              header: "Valor adquisición",
              render: (row) => (row.valor_adquisicion == null ? "—" : formatCop(row.valor_adquisicion)),
            },
            {
              key: "activo",
              header: "Activo",
              render: (row) => <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} />,
            },
            {
              key: "ops",
              header: "",
              render: (row) => (
                <div className="flex flex-wrap justify-end gap-2">
                  <Link to={`/equipos/mantenimientos?equipo_id=${row.id}`} className="text-xs text-[var(--bf-accent)]">
                    Mantenimientos
                  </Link>
                  <Link
                    to={`/equipos/mantenimientos?tab=fallas&equipo_id=${row.id}`}
                    className="text-xs text-[var(--bf-accent)]"
                  >
                    Fallas
                  </Link>
                  {puedeEscribir ? (
                    <>
                      <button
                        type="button"
                        className="bf-btn-secondary !py-1 text-xs"
                        onClick={() => {
                          setFormError(null);
                          form.reset(fromEquipo(row));
                          setEditing(row);
                        }}
                      >
                        Editar
                      </button>
                      <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => setToToggle(row)}>
                        {row.activo ? "Desactivar" : "Activar"}
                      </button>
                    </>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      ) : null}

      <EquipoModal
        open={creating || Boolean(editing)}
        title={editing ? "Editar equipo" : "Nuevo equipo"}
        form={form}
        formError={formError}
        tipos={tiposQuery.data ?? []}
        estados={estadosQuery.data ?? []}
        pending={createMut.isPending || updateMut.isPending}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSubmit={(values) => {
          const payload = toPayload(values);
          if (editing) updateMut.mutate({ id: editing.id, data: payload });
          else createMut.mutate(payload);
        }}
      />

      <ConfirmDialog
        open={Boolean(toToggle)}
        title={toToggle?.activo ? "Desactivar equipo" : "Activar equipo"}
        description="El API no permite eliminar equipos. Se cambia el campo activo."
        confirmLabel={toToggle?.activo ? "Desactivar" : "Activar"}
        onCancel={() => setToToggle(null)}
        onConfirm={() => {
          if (!toToggle) return;
          updateMut.mutate({ id: toToggle.id, data: { activo: !toToggle.activo } });
        }}
      />
    </div>
  );
}

function EquipoModal({
  open,
  title,
  form,
  formError,
  tipos,
  estados,
  pending,
  onClose,
  onSubmit,
}: {
  open: boolean;
  title: string;
  form: ReturnType<typeof useForm<EquipoForm>>;
  formError: string | null;
  tipos: { id: number; nombre: string; activo: boolean }[];
  estados: { id: number; nombre: string; activo: boolean }[];
  pending: boolean;
  onClose: () => void;
  onSubmit: (values: EquipoForm) => void;
}) {
  return (
    <Modal open={open} title={title} size="lg" onClose={onClose}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
        {formError ? (
          <div className="sm:col-span-2">
            <ErrorAlert message={formError} />
          </div>
        ) : null}
        <Field label="Código">
          <input className="bf-input" {...form.register("codigo", { required: true })} />
        </Field>
        <Field label="Nombre">
          <input className="bf-input" {...form.register("nombre", { required: true })} />
        </Field>
        <Field label="Tipo">
          <select className="bf-input" {...form.register("tipo_equipo_id", { valueAsNumber: true })}>
            {tipos.filter((row) => row.activo).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Estado">
          <select className="bf-input" {...form.register("estado_id", { valueAsNumber: true })}>
            {estados.filter((row) => row.activo).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Marca">
          <input className="bf-input" {...form.register("marca")} />
        </Field>
        <Field label="Modelo">
          <input className="bf-input" {...form.register("modelo")} />
        </Field>
        <Field label="Número de serie">
          <input className="bf-input" {...form.register("numero_serie")} />
        </Field>
        <Field label="Fecha de adquisición">
          <input type="date" className="bf-input" {...form.register("fecha_adquisicion")} />
        </Field>
        <Field label="Valor de adquisición">
          <input type="number" step="any" min="0" className="bf-input" {...form.register("valor_adquisicion")} />
        </Field>
        <Field label="Ubicación">
          <input className="bf-input" {...form.register("ubicacion")} />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...form.register("activo")} />
          Activo
        </label>
        <div className="sm:col-span-2">
          <button type="submit" className="bf-btn-primary" disabled={pending || tipos.length === 0 || estados.length === 0}>
            {pending ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-[var(--bf-ink)]">{label}</span>
      {children}
    </label>
  );
}
