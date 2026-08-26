import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { listReferenciasBiofloc } from "../../api/operations";
import { listEspecies, listEtapasProductivas } from "../../api/production";
import { createReferenciaBiofloc, updateReferenciaBiofloc } from "../../api/catalogs";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, parseDecimalInput } from "../../utils/format";
import type { IndicadorBiofloc, ReferenciaBiofloc } from "../../types/operations";

const INDICADORES: { id: IndicadorBiofloc; label: string; unidadSugerida: string }[] = [
  { id: "VOLUMEN_SEDIMENTABLE", label: "Sólidos sedimentables", unidadSugerida: "mL/L" },
  { id: "RELACION_CN", label: "Relación C:N", unidadSugerida: "" },
];

type ReferenciaForm = {
  especie_id: number;
  etapa_productiva_id: number;
  indicador: IndicadorBiofloc | "";
  valor_minimo: string;
  valor_objetivo: string;
  valor_maximo: string;
  unidad: string;
  observaciones: string;
  activo: "true" | "false";
};

function optionalNumber(value: string): number | null {
  return parseDecimalInput(value);
}

function etiquetaIndicador(codigo: string): string {
  return INDICADORES.find((row) => row.id === codigo)?.label ?? codigo;
}

export function ReferenciasBioflocCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ReferenciaBiofloc | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ReferenciaForm>();

  const referenciasQuery = useQuery({
    queryKey: ["referencias-biofloc", "catalog"],
    queryFn: () => listReferenciasBiofloc({ solo_activos: false }),
  });
  const especiesQuery = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });
  const etapasQuery = useQuery({
    queryKey: ["etapas-productivas", "catalog"],
    queryFn: () => listEtapasProductivas(false),
  });

  const especies = useMemo(
    () => new Map((especiesQuery.data ?? []).map((row) => [row.id, row.nombre_comun])),
    [especiesQuery.data],
  );
  const etapas = useMemo(
    () => new Map((etapasQuery.data ?? []).map((row) => [row.id, row.nombre])),
    [etapasQuery.data],
  );

  const createMut = useMutation({
    mutationFn: createReferenciaBiofloc,
    onSuccess: async () => {
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["referencias-biofloc"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateReferenciaBiofloc>[1] }) =>
      updateReferenciaBiofloc(id, data),
    onSuccess: async () => {
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["referencias-biofloc"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      especie_id: 0,
      etapa_productiva_id: 0,
      indicador: "" as IndicadorBiofloc,
      valor_minimo: "",
      valor_objetivo: "",
      valor_maximo: "",
      unidad: "",
      observaciones: "",
      activo: "true",
    });
    setCreating(true);
  }

  function openEdit(row: ReferenciaBiofloc) {
    setFormError(null);
    setEditing(row);
    form.reset({
      especie_id: row.especie_id,
      etapa_productiva_id: row.etapa_productiva_id,
      indicador: row.indicador,
      valor_minimo: row.valor_minimo == null ? "" : String(row.valor_minimo),
      valor_objetivo: row.valor_objetivo == null ? "" : String(row.valor_objetivo),
      valor_maximo: row.valor_maximo == null ? "" : String(row.valor_maximo),
      unidad: row.unidad ?? "",
      observaciones: row.observaciones ?? "",
      activo: row.activo ? "true" : "false",
    });
  }

  const loading = referenciasQuery.isLoading || especiesQuery.isLoading || etapasQuery.isLoading;
  const pending = createMut.isPending || updateMut.isPending;
  const indicadorSeleccionado = form.watch("indicador");

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Referencias Biofloc</h2>
          <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
            Rangos y objetivo de las mediciones que ya existen: sólidos sedimentables y relación C:N.
            Referencia configurada por administrador. No hay semilla científica.
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
          empty="Sin referencia configurada. El administrador debe registrar rangos u objetivo."
          columns={
            [
              {
                key: "indicador",
                header: "Parámetro",
                render: (row) => etiquetaIndicador(row.indicador),
              },
              { key: "especie", header: "Especie", render: (row) => especies.get(row.especie_id) ?? `#${row.especie_id}` },
              { key: "etapa", header: "Etapa", render: (row) => etapas.get(row.etapa_productiva_id) ?? `#${row.etapa_productiva_id}` },
              { key: "unidad", header: "Unidad", render: (row) => row.unidad || "—" },
              {
                key: "min",
                header: "Mínimo",
                render: (row) =>
                  row.valor_minimo == null ? "N/D" : formatNumber(row.valor_minimo, { maximumFractionDigits: 4 }),
              },
              {
                key: "obj",
                header: "Objetivo",
                render: (row) =>
                  row.valor_objetivo == null ? "N/D" : formatNumber(row.valor_objetivo, { maximumFractionDigits: 4 }),
              },
              {
                key: "max",
                header: "Máximo",
                render: (row) =>
                  row.valor_maximo == null ? "N/D" : formatNumber(row.valor_maximo, { maximumFractionDigits: 4 }),
              },
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
                      render: (row: ReferenciaBiofloc) => (
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
            ] satisfies DataTableColumn<ReferenciaBiofloc>[]
          }
        />
      ) : null}

      <Modal open={creating} title="Nueva referencia Biofloc" onClose={() => setCreating(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            setFormError(null);
            createMut.mutate({
              especie_id: Number(values.especie_id),
              etapa_productiva_id: Number(values.etapa_productiva_id),
              indicador: values.indicador as IndicadorBiofloc,
              valor_minimo: optionalNumber(values.valor_minimo),
              valor_objetivo: optionalNumber(values.valor_objetivo),
              valor_maximo: optionalNumber(values.valor_maximo),
              unidad: values.unidad.trim() || null,
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
          <Field label="Parámetro medido">
            <select
              className="bf-input"
              {...form.register("indicador", { required: true })}
              onChange={(event) => {
                const codigo = event.target.value as IndicadorBiofloc;
                form.setValue("indicador", codigo);
                const sugerida = INDICADORES.find((row) => row.id === codigo)?.unidadSugerida ?? "";
                if (!form.getValues("unidad")) form.setValue("unidad", sugerida);
              }}
            >
              <option value="">Seleccione un parámetro</option>
              {INDICADORES.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-[var(--bf-muted)]">
              {indicadorSeleccionado === "RELACION_CN"
                ? "La medición de C:N no tiene unidad en el modelo. Puede dejar la unidad vacía."
                : "La medición de sólidos usa mL/L por defecto en el registro operativo."}
            </p>
          </Field>
          <Field label="Unidad (opcional)">
            <input className="bf-input" {...form.register("unidad")} />
          </Field>
          <Field label="Mínimo">
            <input type="number" step="any" className="bf-input" {...form.register("valor_minimo")} />
          </Field>
          <Field label="Objetivo">
            <input type="number" step="any" className="bf-input" {...form.register("valor_objetivo")} />
          </Field>
          <Field label="Máximo">
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
            {pending ? "Guardando…" : "Crear"}
          </button>
        </form>
      </Modal>

      <Modal open={Boolean(editing)} title="Editar referencia Biofloc" onClose={() => setEditing(null)}>
        {editing ? (
          <form
            className="space-y-3"
            onSubmit={form.handleSubmit((values) => {
              setFormError(null);
              updateMut.mutate({
                id: editing.id,
                data: {
                  valor_minimo: optionalNumber(values.valor_minimo),
                  valor_objetivo: optionalNumber(values.valor_objetivo),
                  valor_maximo: optionalNumber(values.valor_maximo),
                  unidad: values.unidad.trim() || null,
                  observaciones: values.observaciones.trim() || null,
                  activo: values.activo === "true",
                },
              });
            })}
          >
            {formError ? <ErrorAlert message={formError} /> : null}
            <p className="text-sm text-[var(--bf-muted)]">
              {etiquetaIndicador(editing.indicador)} · {especies.get(editing.especie_id)} ·{" "}
              {etapas.get(editing.etapa_productiva_id)}. Especie, etapa e indicador no se cambian en la
              actualización.
            </p>
            <Field label="Unidad (opcional)">
              <input className="bf-input" {...form.register("unidad")} />
            </Field>
            <Field label="Mínimo">
              <input type="number" step="any" className="bf-input" {...form.register("valor_minimo")} />
            </Field>
            <Field label="Objetivo">
              <input type="number" step="any" className="bf-input" {...form.register("valor_objetivo")} />
            </Field>
            <Field label="Máximo">
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
