import { Link } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { createEspecie, listEspecies, updateEspecie } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber } from "../../utils/format";
import type { EspecieCatalogo } from "../../types/production";

type EspecieForm = {
  nombre_comun: string;
  nombre_cientifico: string;
  activo: "true" | "false";
};

export function EspeciesCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<EspecieCatalogo | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<EspecieForm>();

  const query = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });

  const createMut = useMutation({
    mutationFn: createEspecie,
    onSuccess: async () => {
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["especies"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateEspecie>[1] }) =>
      updateEspecie(id, data),
    onSuccess: async () => {
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["especies"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({ nombre_comun: "", nombre_cientifico: "", activo: "true" });
    setCreating(true);
  }

  function openEdit(row: EspecieCatalogo) {
    setFormError(null);
    form.reset({
      nombre_comun: row.nombre_comun,
      nombre_cientifico: row.nombre_cientifico ?? "",
      activo: row.activo ? "true" : "false",
    });
    setEditing(row);
  }

  function submit(values: EspecieForm) {
    setFormError(null);
    const payload = {
      nombre_comun: values.nombre_comun.trim(),
      nombre_cientifico: values.nombre_cientifico.trim() || null,
      activo: values.activo === "true",
    };
    if (editing) {
      updateMut.mutate({ id: editing.id, data: payload });
      return;
    }
    createMut.mutate(payload);
  }

  const pending = createMut.isPending || updateMut.isPending;

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Catálogo de peces / especies</h2>
          <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
            Catálogo maestro. Solo el administrador crea o desactiva especies. No se siembran valores científicos.
          </p>
        </div>
        {canWrite ? (
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            Nueva especie
          </button>
        ) : null}
      </div>

      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay especies registradas."
          columns={
            [
              { key: "comun", header: "Nombre común", render: (row) => row.nombre_comun },
              {
                key: "cientifico",
                header: "Nombre científico",
                render: (row) => row.nombre_cientifico || "N/D",
              },
              {
                key: "activo",
                header: "Estado",
                render: (row) => (
                  <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} />
                ),
              },
              {
                key: "prod",
                header: "Refs. producción",
                render: (row) => formatNumber(row.n_referencias_produccion),
              },
              {
                key: "agua",
                header: "Refs. agua",
                render: (row) => formatNumber(row.n_referencias_agua),
              },
              ...(canWrite
                ? [
                    {
                      key: "acciones",
                      header: "",
                      className: "text-right",
                      render: (row: EspecieCatalogo) => (
                        <div className="flex flex-wrap justify-end gap-2">
                          <Link
                            to="/catalogos?seccion=produccion"
                            className="bf-btn-secondary !px-2 !py-1 text-xs"
                          >
                            Ver referencias
                          </Link>
                          <button
                            type="button"
                            className="bf-btn-secondary !px-2 !py-1 text-xs"
                            onClick={() => openEdit(row)}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="bf-btn-secondary !px-2 !py-1 text-xs"
                            onClick={() =>
                              updateMut.mutate({
                                id: row.id,
                                data: { activo: !row.activo },
                              })
                            }
                          >
                            {row.activo ? "Desactivar" : "Activar"}
                          </button>
                        </div>
                      ),
                    },
                  ]
                : []),
            ] satisfies DataTableColumn<EspecieCatalogo>[]
          }
        />
      ) : null}

      <Modal
        open={creating || Boolean(editing)}
        title={editing ? "Editar especie" : "Nueva especie"}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
      >
        <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Nombre común">
            <input className="bf-input" {...form.register("nombre_comun", { required: true })} />
          </Field>
          <Field label="Nombre científico (opcional)">
            <input className="bf-input" {...form.register("nombre_cientifico")} />
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...form.register("activo")}>
              <option value="true">Activo</option>
              <option value="false">Inactivo</option>
            </select>
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={pending}>
            {pending ? "Guardando…" : "Guardar"}
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
