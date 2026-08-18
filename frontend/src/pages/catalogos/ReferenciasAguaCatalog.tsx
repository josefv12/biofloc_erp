import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { listParametrosAgua, listReferenciasAgua } from "../../api/operations";
import { listLotes } from "../../api/production";
import { updateReferenciaAgua } from "../../api/catalogs";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber } from "../../utils/format";
import type { ReferenciaAgua } from "../../types/operations";

type ReferenciaForm = {
  valor_minimo: string;
  valor_maximo: string;
  observaciones: string;
  activo: "true" | "false";
};

function optionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  return Number(trimmed);
}

export function ReferenciasAguaCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
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
  const lotesQuery = useQuery({
    queryKey: ["lotes"],
    queryFn: () => listLotes(),
  });

  const parametros = useMemo(
    () => new Map((parametrosQuery.data ?? []).map((row) => [row.id, row])),
    [parametrosQuery.data],
  );
  const especies = useMemo(() => {
    const map = new Map<number, string>();
    for (const lote of lotesQuery.data ?? []) {
      if (!map.has(lote.especie_id)) map.set(lote.especie_id, lote.especie.nombre_comun);
    }
    return map;
  }, [lotesQuery.data]);
  const etapas = useMemo(() => {
    const map = new Map<number, string>();
    for (const lote of lotesQuery.data ?? []) {
      if (!map.has(lote.etapa_productiva_id)) map.set(lote.etapa_productiva_id, lote.etapa_productiva.nombre);
    }
    return map;
  }, [lotesQuery.data]);

  const mutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateReferenciaAgua>[1] }) =>
      updateReferenciaAgua(id, data),
    onSuccess: async () => {
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["referencias-agua"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function labelEspecie(id: number): string {
    return especies.get(id) ?? `Especie #${id}`;
  }

  function labelEtapa(id: number): string {
    return etapas.get(id) ?? `Etapa #${id}`;
  }

  function openEdit(row: ReferenciaAgua) {
    setFormError(null);
    setEditing(row);
    form.reset({
      valor_minimo: row.valor_minimo == null ? "" : String(row.valor_minimo),
      valor_maximo: row.valor_maximo == null ? "" : String(row.valor_maximo),
      observaciones: row.observaciones ?? "",
      activo: row.activo ? "true" : "false",
    });
  }

  return (
    <section className="mb-8">
      <div className="mb-3">
        <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Referencias de agua</h2>
        <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
          El API permite crear referencias con especie_id, etapa_productiva_id y parametro_id, pero no existe
          un GET de especies ni de etapas productivas. Esta pantalla no inventa esos catálogos ni pide IDs a
          mano. Puede consultar las referencias existentes y, si tiene permiso, editar mínimo, máximo,
          observaciones y activo. Especie y etapa se muestran con el nombre si ya aparecen en un lote; si no,
          solo el identificador que entrega el API.
        </p>
      </div>

      {referenciasQuery.isLoading || parametrosQuery.isLoading ? <LoadingState /> : null}
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
                key: "min",
                header: "Mínimo",
                render: (row) => formatNumber(row.valor_minimo, { maximumFractionDigits: 4 }),
              },
              {
                key: "max",
                header: "Máximo",
                render: (row) => formatNumber(row.valor_maximo, { maximumFractionDigits: 4 }),
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

      <Modal open={Boolean(editing)} title="Editar referencia de agua" onClose={() => setEditing(null)}>
        {editing ? (
          <form
            className="space-y-3"
            onSubmit={form.handleSubmit((values) => {
              setFormError(null);
              mutation.mutate({
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
            <button type="submit" className="bf-btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? "Guardando…" : "Guardar"}
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
