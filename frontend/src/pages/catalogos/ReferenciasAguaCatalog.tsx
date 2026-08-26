import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { listParametrosAgua, listReferenciasAgua } from "../../api/operations";
import { listEspecies, listEtapasProductivas } from "../../api/production";
import { createReferenciaAgua, updateReferenciaAgua } from "../../api/catalogs";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, parseDecimalInput } from "../../utils/format";
import type { ReferenciaAgua } from "../../types/operations";

type ReferenciaForm = {
  especie_id: number;
  etapa_productiva_id: number;
  parametro_id: number;
  valor_minimo: string;
  valor_maximo: string;
  observaciones: string;
  activo: "true" | "false";
};

function optionalNumber(value: string): number | null {
  return parseDecimalInput(value);
}

export function ReferenciasAguaCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ReferenciaAgua | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ReferenciaForm>();

  const referenciasQuery = useQuery({
    queryKey: ["referencias-agua", "catalog"],
    queryFn: () => listReferenciasAgua({ solo_activos: false }),
  });
  const parametrosQuery = useQuery({
    queryKey: ["parametros-agua", "catalog"],
    queryFn: () => listParametrosAgua(false),
  });
  const especiesQuery = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });
  const etapasQuery = useQuery({
    queryKey: ["etapas-productivas", "catalog"],
    queryFn: () => listEtapasProductivas(false),
  });

  const parametros = useMemo(
    () => new Map((parametrosQuery.data ?? []).map((row) => [row.id, row])),
    [parametrosQuery.data],
  );
  const especies = useMemo(
    () => new Map((especiesQuery.data ?? []).map((row) => [row.id, row.nombre_comun])),
    [especiesQuery.data],
  );
  const etapas = useMemo(
    () => new Map((etapasQuery.data ?? []).map((row) => [row.id, row.nombre])),
    [etapasQuery.data],
  );

  const createMut = useMutation({
    mutationFn: createReferenciaAgua,
    onSuccess: async () => {
      setCreating(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["referencias-agua"] }),
        queryClient.invalidateQueries({ queryKey: ["especies"] }),
      ]);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateReferenciaAgua>[1] }) =>
      updateReferenciaAgua(id, data),
    onSuccess: async () => {
      setEditing(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["referencias-agua"] }),
        queryClient.invalidateQueries({ queryKey: ["especies"] }),
      ]);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function labelEspecie(id: number): string {
    return especies.get(id) ?? `Especie #${id}`;
  }

  function labelEtapa(id: number): string {
    return etapas.get(id) ?? `Etapa #${id}`;
  }

  function openCreate() {
    setFormError(null);
    form.reset({
      especie_id: 0,
      etapa_productiva_id: 0,
      parametro_id: 0,
      valor_minimo: "",
      valor_maximo: "",
      observaciones: "",
      activo: "true",
    });
    setCreating(true);
  }

  function openEdit(row: ReferenciaAgua) {
    setFormError(null);
    setEditing(row);
    form.reset({
      especie_id: row.especie_id,
      etapa_productiva_id: row.etapa_productiva_id,
      parametro_id: row.parametro_id,
      valor_minimo: row.valor_minimo == null ? "" : String(row.valor_minimo),
      valor_maximo: row.valor_maximo == null ? "" : String(row.valor_maximo),
      observaciones: row.observaciones ?? "",
      activo: row.activo ? "true" : "false",
    });
  }

  const loading =
    referenciasQuery.isLoading ||
    parametrosQuery.isLoading ||
    especiesQuery.isLoading ||
    etapasQuery.isLoading;
  const pending = createMut.isPending || updateMut.isPending;

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Referencias de agua</h2>
          <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
            Rangos mínimo y máximo por especie, etapa y parámetro. Referencia configurada por
            administrador. La etapa se conserva aunque hoy algunos valores coincidan.
          </p>
        </div>
        {canWrite ? (
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            Nueva referencia
          </button>
        ) : null}
      </div>

      {loading ? <LoadingState /> : null}
      {referenciasQuery.isError ? <ErrorAlert message={apiErrorMessage(referenciasQuery.error)} /> : null}
      {referenciasQuery.data ? (
        <DataTable
          rows={referenciasQuery.data}
          rowKey={(row) => row.id}
          empty="No hay referencias de agua."
          columns={
            [
              {
                key: "parametro",
                header: "Parámetro",
                render: (row) => parametros.get(row.parametro_id)?.nombre ?? `#${row.parametro_id}`,
              },
              { key: "especie", header: "Especie", render: (row) => labelEspecie(row.especie_id) },
              { key: "etapa", header: "Etapa", render: (row) => labelEtapa(row.etapa_productiva_id) },
              {
                key: "unidad",
                header: "Unidad",
                render: (row) => parametros.get(row.parametro_id)?.unidad ?? "—",
              },
              {
                key: "min",
                header: "Mínimo",
                render: (row) =>
                  row.valor_minimo == null
                    ? "N/D"
                    : formatNumber(row.valor_minimo, { maximumFractionDigits: 4 }),
              },
              {
                key: "max",
                header: "Máximo",
                render: (row) =>
                  row.valor_maximo == null
                    ? "N/D"
                    : formatNumber(row.valor_maximo, { maximumFractionDigits: 4 }),
              },
              { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
              {
                key: "activo",
                header: "Estado",
                render: (row) => (
                  <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} />
                ),
              },
              ...(canWrite
                ? [
                    {
                      key: "acciones",
                      header: "",
                      className: "text-right",
                      render: (row: ReferenciaAgua) => (
                        <button
                          type="button"
                          className="bf-btn-secondary !px-2 !py-1 text-xs"
                          onClick={() => openEdit(row)}
                        >
                          Editar
                        </button>
                      ),
                    },
                  ]
                : []),
            ] satisfies DataTableColumn<ReferenciaAgua>[]
          }
        />
      ) : null}

      <Modal
        open={creating}
        title="Nueva referencia de agua"
        onClose={() => setCreating(false)}
      >
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            setFormError(null);
            createMut.mutate({
              especie_id: Number(values.especie_id),
              etapa_productiva_id: Number(values.etapa_productiva_id),
              parametro_id: Number(values.parametro_id),
              valor_minimo: optionalNumber(values.valor_minimo),
              valor_maximo: optionalNumber(values.valor_maximo),
              observaciones: values.observaciones.trim() || null,
              activo: values.activo === "true",
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Especie">
            <select className="bf-input" {...form.register("especie_id", { valueAsNumber: true, required: true })}>
              <option value="">Seleccione una especie</option>
              {(especiesQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre_comun}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Etapa productiva">
            <select className="bf-input" {...form.register("etapa_productiva_id", { valueAsNumber: true, required: true })}>
              <option value="">Seleccione una etapa</option>
              {(etapasQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Parámetro">
            <select className="bf-input" {...form.register("parametro_id", { valueAsNumber: true, required: true })}>
              <option value="">Seleccione un parámetro</option>
              {(parametrosQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre} ({row.unidad})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Valor mínimo">
            <input type="number" step="any" className="bf-input" placeholder="Ingrese el mínimo" {...form.register("valor_minimo")} />
          </Field>
          <Field label="Valor máximo">
            <input type="number" step="any" className="bf-input" placeholder="Ingrese el máximo" {...form.register("valor_maximo")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...form.register("activo")}>
              <option value="true">Activo</option>
              <option value="false">Inactivo</option>
            </select>
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={pending}>
            {pending ? "Guardando…" : "Crear"}
          </button>
        </form>
      </Modal>

      <Modal open={Boolean(editing)} title="Editar referencia de agua" onClose={() => setEditing(null)}>
        {editing ? (
          <form
            className="space-y-3"
            onSubmit={form.handleSubmit((values) => {
              setFormError(null);
              updateMut.mutate({
                id: editing.id,
                data: {
                  valor_minimo: optionalNumber(values.valor_minimo),
                  valor_maximo: optionalNumber(values.valor_maximo),
                  observaciones: values.observaciones.trim() || null,
                  activo: values.activo === "true",
                },
              });
            })}
          >
            {formError ? <ErrorAlert message={formError} /> : null}
            <p className="text-sm text-[var(--bf-muted)]">
              Parámetro: {parametros.get(editing.parametro_id)?.nombre ?? `#${editing.parametro_id}`} ·{" "}
              {labelEspecie(editing.especie_id)} · {labelEtapa(editing.etapa_productiva_id)}. Esos vínculos no
              se pueden cambiar en la actualización.
            </p>
            <Field label="Valor mínimo">
              <input type="number" step="any" className="bf-input" {...form.register("valor_minimo")} />
            </Field>
            <Field label="Valor máximo">
              <input type="number" step="any" className="bf-input" {...form.register("valor_maximo")} />
            </Field>
            <Field label="Observaciones">
              <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
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
        ) : null}
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
