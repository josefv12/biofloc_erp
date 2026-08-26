import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import {
  createReferenciaProduccion,
  listEspecies,
  listEtapasProductivas,
  listReferenciasProduccion,
  updateReferenciaProduccion,
} from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, parseDecimalInput } from "../../utils/format";
import { etiquetaRangoSemanas, etiquetaRaciones } from "../../utils/semanaReferencia";
import type { ReferenciaProduccion } from "../../types/production";

const FASES = ["Inicio", "Levante", "Engorde"] as const;

type ReferenciaForm = {
  especie_id: number;
  etapa_productiva_id: number;
  semana_desde: number | "";
  semana_hasta: number | "";
  peso_esperado_g: string;
  tasa_alimentacion_pct: string;
  raciones_min: string;
  raciones_max: string;
  fase: string;
  observaciones: string;
  activo: "true" | "false";
};

function optionalNumber(value: string): number | null {
  return parseDecimalInput(value);
}

function optionalInt(value: string): number | null {
  const texto = value.trim();
  if (!texto) return null;
  const n = Number(texto);
  return Number.isInteger(n) ? n : null;
}

function nd(value: string | number | null): string {
  return value == null ? "N/D — referencia no registrada" : formatNumber(value, { maximumFractionDigits: 3 });
}

export function ReferenciasProduccionCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
  const [especieFiltro, setEspecieFiltro] = useState<number | "todas">("todas");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ReferenciaProduccion | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ReferenciaForm>();

  const especiesQuery = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });
  const etapasQuery = useQuery({
    queryKey: ["etapas-productivas", "catalog"],
    queryFn: () => listEtapasProductivas(false),
  });
  const referenciasQuery = useQuery({
    queryKey: ["referencias-produccion", "catalog"],
    queryFn: () => listReferenciasProduccion({ solo_activos: false }),
  });

  const especies = useMemo(
    () => new Map((especiesQuery.data ?? []).map((row) => [row.id, row])),
    [especiesQuery.data],
  );
  const filas = useMemo(() => {
    const todas = referenciasQuery.data ?? [];
    if (especieFiltro === "todas") return todas;
    return todas.filter((row) => row.especie_id === especieFiltro);
  }, [referenciasQuery.data, especieFiltro]);

  const createMut = useMutation({
    mutationFn: createReferenciaProduccion,
    onSuccess: async () => {
      setCreating(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["referencias-produccion"] }),
        queryClient.invalidateQueries({ queryKey: ["especies"] }),
      ]);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateReferenciaProduccion>[1] }) =>
      updateReferenciaProduccion(id, data),
    onSuccess: async () => {
      setEditing(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["referencias-produccion"] }),
        queryClient.invalidateQueries({ queryKey: ["especies"] }),
      ]);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      especie_id: 0,
      etapa_productiva_id: 0,
      semana_desde: "",
      semana_hasta: "",
      peso_esperado_g: "",
      tasa_alimentacion_pct: "",
      raciones_min: "",
      raciones_max: "",
      fase: "",
      observaciones: "",
      activo: "true",
    });
    setCreating(true);
  }

  function openEdit(row: ReferenciaProduccion) {
    setFormError(null);
    form.reset({
      especie_id: row.especie_id,
      etapa_productiva_id: row.etapa_productiva_id,
      semana_desde: row.semana_desde,
      semana_hasta: row.semana_hasta,
      peso_esperado_g: row.peso_esperado_g == null ? "" : String(row.peso_esperado_g),
      tasa_alimentacion_pct: row.tasa_alimentacion_pct == null ? "" : String(row.tasa_alimentacion_pct),
      raciones_min: row.raciones_min == null ? "" : String(row.raciones_min),
      raciones_max: row.raciones_max == null ? "" : String(row.raciones_max),
      fase: row.fase ?? "",
      observaciones: row.observaciones ?? "",
      activo: row.activo ? "true" : "false",
    });
    setEditing(row);
  }

  function submit(values: ReferenciaForm) {
    setFormError(null);
    const semanaDesde = Number(values.semana_desde);
    const semanaHasta = values.semana_hasta === "" ? semanaDesde : Number(values.semana_hasta);
    const rMin = optionalInt(values.raciones_min);
    const rMaxRaw = optionalInt(values.raciones_max);
    const payload = {
      especie_id: Number(values.especie_id),
      etapa_productiva_id: Number(values.etapa_productiva_id),
      semana_desde: semanaDesde,
      semana_hasta: semanaHasta,
      peso_esperado_g: optionalNumber(values.peso_esperado_g),
      tasa_alimentacion_pct: optionalNumber(values.tasa_alimentacion_pct),
      raciones_min: rMin,
      raciones_max: rMaxRaw ?? rMin,
      fase: values.fase.trim() || null,
      observaciones: values.observaciones.trim() || null,
      activo: values.activo === "true",
    };
    if (editing) {
      updateMut.mutate({ id: editing.id, data: payload });
      return;
    }
    createMut.mutate(payload);
  }

  const pending = createMut.isPending || updateMut.isPending;
  const especieSeleccionada = especieFiltro === "todas" ? null : especies.get(especieFiltro);

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">
            Referencias de producción
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
            Catálogo oficial: una fila por semana. Peso, tasa, raciones (mín–máx, nunca un promedio) y fase
            de alimentación. La fase no sustituye ni equivale a la etapa productiva.
          </p>
        </div>
        {canWrite ? (
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            Nueva referencia
          </button>
        ) : null}
      </div>

      <label className="mb-4 block max-w-sm text-sm">
        <span className="mb-1 block font-medium text-[var(--bf-ink)]">Ver por especie</span>
        <select
          className="bf-input"
          value={especieFiltro === "todas" ? "todas" : String(especieFiltro)}
          onChange={(evento) => {
            const value = evento.target.value;
            setEspecieFiltro(value === "todas" ? "todas" : Number(value));
          }}
        >
          <option value="todas">Todas</option>
          {(especiesQuery.data ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.nombre_comun}
            </option>
          ))}
        </select>
      </label>

      {especieSeleccionada ? (
        <p className="mb-3 text-sm text-[var(--bf-muted)]">
          {especieSeleccionada.nombre_comun}: {formatNumber(especieSeleccionada.n_referencias_produccion)}{" "}
          referencia(s) de producción · {formatNumber(especieSeleccionada.n_referencias_agua)} de agua ·
          Biofloc: sin referencias.
        </p>
      ) : null}

      {referenciasQuery.isLoading || especiesQuery.isLoading || etapasQuery.isLoading ? (
        <LoadingState />
      ) : null}
      {referenciasQuery.isError ? <ErrorAlert message={apiErrorMessage(referenciasQuery.error)} /> : null}

      {referenciasQuery.data && filas.length === 0 ? (
        <p className="mb-4 rounded-lg border border-dashed border-[var(--bf-border)] px-4 py-6 text-center text-sm text-[var(--bf-muted)]">
          N/D — referencia no registrada
        </p>
      ) : null}

      {filas.length > 0 ? (
        <DataTable
          rows={filas}
          rowKey={(row) => row.id}
          empty="N/D — referencia no registrada"
          columns={
            [
              {
                key: "especie",
                header: "Especie",
                render: (row) => especies.get(row.especie_id)?.nombre_comun ?? `Especie #${row.especie_id}`,
              },
              {
                key: "semana",
                header: "Semana",
                render: (row) => etiquetaRangoSemanas(row.semana_desde, row.semana_hasta),
              },
              { key: "peso", header: "Peso esperado", render: (row) => nd(row.peso_esperado_g) },
              { key: "tasa", header: "Tasa", render: (row) => nd(row.tasa_alimentacion_pct) },
              {
                key: "raciones",
                header: "Raciones",
                render: (row) => etiquetaRaciones(row.raciones_min, row.raciones_max),
              },
              { key: "fase", header: "Fase", render: (row) => row.fase || "N/D" },
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
                      render: (row: ReferenciaProduccion) => (
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
            ] satisfies DataTableColumn<ReferenciaProduccion>[]
          }
        />
      ) : null}

      <Modal
        open={creating || Boolean(editing)}
        title={editing ? "Editar referencia de producción" : "Nueva referencia de producción"}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
      >
        <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
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
          <Field label="Etapa productiva (esquema; no equivale a fase)">
            <select className="bf-input" {...form.register("etapa_productiva_id", { valueAsNumber: true, required: true })}>
              <option value="">Seleccione una etapa</option>
              {(etapasQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Semana desde">
            <input
              type="number"
              min="0"
              className="bf-input"
              placeholder="Semana desde"
              {...form.register("semana_desde", { required: true })}
            />
          </Field>
          <Field label="Semana hasta">
            <input
              type="number"
              min="0"
              className="bf-input"
              placeholder="Igual a desde si es una sola semana"
              {...form.register("semana_hasta")}
            />
          </Field>
          <Field label="Peso esperado (g)">
            <input type="number" step="any" min="0" className="bf-input" placeholder="Ingrese el peso esperado" {...form.register("peso_esperado_g")} />
          </Field>
          <Field label="Tasa de alimentación (%)">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              placeholder="Ingrese la tasa"
              {...form.register("tasa_alimentacion_pct")}
            />
          </Field>
          <Field label="Raciones mínimas / día">
            <input type="number" min="0" step="1" className="bf-input" placeholder="Ej. 6" {...form.register("raciones_min")} />
          </Field>
          <Field label="Raciones máximas / día">
            <input type="number" min="0" step="1" className="bf-input" placeholder="Ej. 8. Si vacío, igual al mínimo." {...form.register("raciones_max")} />
          </Field>
          <Field label="Fase">
            <select className="bf-input" {...form.register("fase")}>
              <option value="">N/D</option>
              {FASES.map((fase) => (
                <option key={fase} value={fase}>
                  {fase}
                </option>
              ))}
            </select>
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
