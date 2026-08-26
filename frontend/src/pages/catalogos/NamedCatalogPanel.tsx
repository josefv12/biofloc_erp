import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { apiErrorMessage } from "../../utils/apiError";

export type CatalogField =
  | "nombre"
  | "descripcion"
  | "unidad"
  | "simbolo"
  | "prioridad"
  | "afecta_stock"
  | "activo";

export type CatalogRow = {
  id: number;
  nombre: string;
  descripcion?: string | null;
  unidad?: string;
  simbolo?: string;
  prioridad?: number;
  afecta_stock?: -1 | 1;
  activo?: boolean;
};

type CatalogForm = {
  nombre: string;
  descripcion: string;
  unidad: string;
  simbolo: string;
  prioridad: number;
  afecta_stock: "-1" | "1";
  activo: "true" | "false";
};

export type NamedCatalogSpec = {
  title: string;
  queryKey: readonly unknown[];
  list: () => Promise<CatalogRow[]>;
  create: (body: Record<string, unknown>) => Promise<unknown>;
  update: (id: number, body: Record<string, unknown>) => Promise<unknown>;
  fields: CatalogField[];
  canWrite: boolean;
  createLabel?: string;
  note?: string;
  lockNombre?: (nombre: string) => boolean;
  lockNombreHint?: string;
};

function hasField(fields: CatalogField[], field: CatalogField): boolean {
  return fields.includes(field);
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function buildPayload(fields: CatalogField[], values: CatalogForm, omitNombre: boolean): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (hasField(fields, "nombre") && !omitNombre) body.nombre = values.nombre.trim();
  if (hasField(fields, "descripcion")) body.descripcion = emptyToNull(values.descripcion);
  if (hasField(fields, "unidad")) body.unidad = values.unidad.trim();
  if (hasField(fields, "simbolo")) body.simbolo = values.simbolo.trim();
  if (hasField(fields, "prioridad")) body.prioridad = Number(values.prioridad);
  if (hasField(fields, "afecta_stock")) body.afecta_stock = Number(values.afecta_stock);
  if (hasField(fields, "activo")) body.activo = values.activo === "true";
  return body;
}

export function NamedCatalogPanel({ spec }: { spec: NamedCatalogSpec }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CatalogRow | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<CatalogForm>();
  const nombreLocked = Boolean(editing && spec.lockNombre?.(editing.nombre));

  const listQuery = useQuery({
    queryKey: spec.queryKey,
    queryFn: spec.list,
  });

  const mutation = useMutation({
    mutationFn: (payload: { id?: number; body: Record<string, unknown> }) =>
      payload.id == null ? spec.create(payload.body) : spec.update(payload.id, payload.body),
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: [spec.queryKey[0]] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    setEditing(null);
    form.reset({
      nombre: "",
      descripcion: "",
      unidad: "",
      simbolo: "",
      prioridad: 1,
      afecta_stock: "1",
      activo: "true",
    });
    setOpen(true);
  }

  function openEdit(row: CatalogRow) {
    setFormError(null);
    setEditing(row);
    form.reset({
      nombre: row.nombre,
      descripcion: row.descripcion ?? "",
      unidad: row.unidad ?? "",
      simbolo: row.simbolo ?? "",
      prioridad: row.prioridad ?? 1,
      afecta_stock: row.afecta_stock === -1 ? "-1" : "1",
      activo: row.activo === false ? "false" : "true",
    });
    setOpen(true);
  }

  const columns: DataTableColumn<CatalogRow>[] = [
    { key: "nombre", header: "Nombre" },
  ];
  if (hasField(spec.fields, "unidad")) {
    columns.push({ key: "unidad", header: "Unidad", render: (row) => row.unidad ?? "—" });
  }
  if (hasField(spec.fields, "simbolo")) {
    columns.push({ key: "simbolo", header: "Símbolo", render: (row) => row.simbolo ?? "—" });
  }
  if (hasField(spec.fields, "descripcion")) {
    columns.push({ key: "descripcion", header: "Descripción", render: (row) => row.descripcion || "—" });
  }
  if (hasField(spec.fields, "prioridad")) {
    columns.push({ key: "prioridad", header: "Prioridad", render: (row) => String(row.prioridad ?? "—") });
  }
  if (hasField(spec.fields, "afecta_stock")) {
    columns.push({
      key: "afecta_stock",
      header: "afecta_stock",
      render: (row) => (row.afecta_stock === -1 ? "−1" : row.afecta_stock === 1 ? "+1" : "—"),
    });
  }
  if (hasField(spec.fields, "activo")) {
    columns.push({
      key: "activo",
      header: "Estado",
      render: (row) => (
        <StatusBadge
          label={row.activo ? "Activo" : "Inactivo"}
          tone={row.activo ? "ok" : "neutral"}
        />
      ),
    });
  }
  if (spec.canWrite) {
    columns.push({
      key: "acciones",
      header: "",
      className: "text-right",
      render: (row) => (
        <button
          type="button"
          className="bf-btn-secondary !px-2 !py-1 text-xs"
          onClick={(event) => {
            event.stopPropagation();
            openEdit(row);
          }}
        >
          Editar
        </button>
      ),
    });
  }

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">{spec.title}</h2>
          {spec.note ? <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">{spec.note}</p> : null}
        </div>
        {spec.canWrite ? (
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            {spec.createLabel ?? "Nuevo"}
          </button>
        ) : null}
      </div>

      {listQuery.isLoading ? <LoadingState /> : null}
      {listQuery.isError ? <ErrorAlert message={apiErrorMessage(listQuery.error)} /> : null}
      {listQuery.data ? (
        <DataTable
          rows={listQuery.data}
          rowKey={(row) => row.id}
          empty="No hay registros en este catálogo."
          columns={columns}
        />
      ) : null}

      <Modal
        open={open}
        title={editing ? `Editar ${spec.title.toLowerCase()}` : `Nuevo · ${spec.title}`}
        onClose={() => setOpen(false)}
      >
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            setFormError(null);
            mutation.mutate({
              id: editing?.id,
              body: buildPayload(spec.fields, values, nombreLocked),
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {hasField(spec.fields, "nombre") ? (
            <Field label="Nombre">
              <input
                className="bf-input"
                maxLength={80}
                disabled={nombreLocked}
                {...form.register("nombre", { required: !nombreLocked })}
              />
            </Field>
          ) : null}
          {nombreLocked && spec.lockNombreHint ? (
            <p className="text-sm text-[var(--bf-muted)]">{spec.lockNombreHint}</p>
          ) : null}
          {hasField(spec.fields, "unidad") ? (
            <Field label="Unidad">
              <input className="bf-input" maxLength={30} {...form.register("unidad", { required: true })} />
            </Field>
          ) : null}
          {hasField(spec.fields, "simbolo") ? (
            <Field label="Símbolo">
              <input className="bf-input" maxLength={10} {...form.register("simbolo", { required: true })} />
            </Field>
          ) : null}
          {hasField(spec.fields, "descripcion") ? (
            <Field label="Descripción">
              <textarea className="bf-input min-h-20" {...form.register("descripcion")} />
            </Field>
          ) : null}
          {hasField(spec.fields, "prioridad") ? (
            <Field label="Prioridad">
              <input
                type="number"
                min={1}
                step={1}
                className="bf-input"
                {...form.register("prioridad", { valueAsNumber: true, required: true, min: 1 })}
              />
            </Field>
          ) : null}
          {hasField(spec.fields, "afecta_stock") ? (
            <Field label="Efecto sobre el stock">
              <select className="bf-input" {...form.register("afecta_stock", { required: true })}>
                <option value="1">+1</option>
                <option value="-1">−1</option>
              </select>
            </Field>
          ) : null}
          {hasField(spec.fields, "activo") ? (
            <Field label="Estado">
              <select className="bf-input" {...form.register("activo")}>
                <option value="true">Activo</option>
                <option value="false">Inactivo</option>
              </select>
            </Field>
          ) : null}
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Guardando…" : "Guardar"}
          </button>
        </form>
      </Modal>
    </section>
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
