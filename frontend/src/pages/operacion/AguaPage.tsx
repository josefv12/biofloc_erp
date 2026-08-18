import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import {
  createMedicionAgua,
  listMedicionesAgua,
  listParametrosAgua,
  listReferenciasAgua,
} from "../../api/operations";
import { getLote, listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import {
  datetimeLocalToIso,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import type { MedicionAgua, MedicionAguaCreate, ParametroAgua, ReferenciaAgua } from "../../types/operations";
import type { Lote } from "../../types/production";

export function AguaPage() {
  const [params, setParams] = useSearchParams();
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const parametroId = Number(params.get("parametro_id") ?? "") || undefined;

  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const parametrosQuery = useQuery({ queryKey: ["parametros-agua"], queryFn: () => listParametrosAgua(true) });
  const loteQuery = useQuery({
    queryKey: ["lote", loteId],
    queryFn: () => getLote(loteId!),
    enabled: Boolean(loteId),
  });
  const refsQuery = useQuery({
    queryKey: ["referencias-agua", loteQuery.data?.especie_id, loteQuery.data?.etapa_productiva_id],
    queryFn: () =>
      listReferenciasAgua({
        especie_id: loteQuery.data!.especie_id,
        etapa_productiva_id: loteQuery.data!.etapa_productiva_id,
        solo_activos: true,
      }),
    enabled: Boolean(loteQuery.data),
  });
  const medicionesQuery = useQuery({
    queryKey: ["mediciones-agua", loteId, parametroId],
    queryFn: () => listMedicionesAgua({ lote_id: loteId, parametro_id: parametroId }),
  });

  return (
    <div>
      <PageHeader
        title="Agua"
        description="Mediciones de calidad de agua. Las referencias se muestran solo si el API las entrega para la especie y etapa del lote; no se clasifican en React."
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Lote</span>
          <select
            className="bf-input"
            value={loteId ?? ""}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("lote_id", event.target.value);
              else next.delete("lote_id");
              setParams(next);
            }}
          >
            <option value="">Todos</option>
            {(lotesQuery.data ?? []).map((lote) => (
              <option key={lote.id} value={lote.id}>
                {lote.codigo}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Parámetro</span>
          <select
            className="bf-input"
            value={parametroId ?? ""}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("parametro_id", event.target.value);
              else next.delete("parametro_id");
              setParams(next);
            }}
          >
            <option value="">Todos</option>
            {(parametrosQuery.data ?? []).map((parametro) => (
              <option key={parametro.id} value={parametro.id}>
                {parametro.nombre} ({parametro.unidad})
              </option>
            ))}
          </select>
        </label>
      </div>
      <AguaMedicionesPanel
        loteId={loteId}
        lote={loteQuery.data}
        lotes={lotesQuery.data ?? []}
        parametros={parametrosQuery.data ?? []}
        referencias={refsQuery.data ?? []}
        mediciones={medicionesQuery.data}
        loading={medicionesQuery.isLoading}
        error={medicionesQuery.error}
        onRetry={() => void medicionesQuery.refetch()}
        compact={false}
      />
    </div>
  );
}

type PanelProps = {
  loteId?: number;
  lote?: Lote;
  lotes: Lote[];
  parametros: ParametroAgua[];
  referencias: ReferenciaAgua[];
  mediciones: MedicionAgua[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  compact: boolean;
};

export function AguaMedicionesPanel({
  loteId,
  lote,
  lotes,
  parametros,
  referencias,
  mediciones,
  loading,
  error,
  onRetry,
  compact,
}: PanelProps) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarAgua");
  const parametrosMap = useMemo(() => new Map(parametros.map((row) => [row.id, row])), [parametros]);
  const lotesMap = useMemo(() => new Map(lotes.map((row) => [row.id, row])), [lotes]);
  const rows = compact ? (mediciones ?? []).slice(0, 5) : (mediciones ?? []);

  const form = useForm({
    defaultValues: {
      lote_id: loteId ?? 0,
      parametro_id: parametros[0]?.id ?? 0,
      fecha_hora: toDatetimeLocalValue(),
      valor: 0,
      observaciones: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: MedicionAguaCreate) => createMedicionAgua(data),
    onSuccess: async () => {
      setOpen(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["mediciones-agua"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  function referenciaDe(parametroId: number): ReferenciaAgua | undefined {
    if (!lote) return undefined;
    return referencias.find(
      (row) =>
        row.parametro_id === parametroId &&
        row.especie_id === lote.especie_id &&
        row.etapa_productiva_id === lote.etapa_productiva_id,
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-[var(--bf-muted)]">
          {compact ? "Últimas mediciones de este lote" : "Historial de mediciones"}
        </p>
        <div className="flex gap-2">
          {compact && loteId ? (
            <Link to={`/operacion/agua?lote_id=${loteId}`} className="bf-btn-secondary">
              Ver todas
            </Link>
          ) : null}
          {puedeRegistrar ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  lote_id: loteId ?? lotes[0]?.id ?? 0,
                  parametro_id: parametros[0]?.id ?? 0,
                  fecha_hora: toDatetimeLocalValue(),
                  valor: 0,
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar medición
            </button>
          ) : null}
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? (
        <div className="space-y-3">
          <ErrorAlert message={apiErrorMessage(error)} />
          <button type="button" className="bf-btn-primary" onClick={onRetry}>
            Reintentar
          </button>
        </div>
      ) : null}

      {mediciones ? (
        <DataTable
          rows={rows}
          rowKey={(row) => row.id}
          empty="No hay mediciones de agua."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            ...(!loteId
              ? [
                  {
                    key: "lote",
                    header: "Lote",
                    render: (row: MedicionAgua) => lotesMap.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
                  },
                ]
              : []),
            {
              key: "parametro",
              header: "Parámetro",
              render: (row) => parametrosMap.get(row.parametro_id)?.nombre ?? `#${row.parametro_id}`,
            },
            {
              key: "valor",
              header: "Valor",
              render: (row) => {
                const unidad = parametrosMap.get(row.parametro_id)?.unidad;
                return `${formatNumber(row.valor, { maximumFractionDigits: 4 })}${unidad ? ` ${unidad}` : ""}`;
              },
            },
            {
              key: "ref",
              header: "Referencia API",
              render: (row) => {
                if (!lote) return "Seleccione un lote";
                const ref = referenciaDe(row.parametro_id);
                if (!ref) return "No existe referencia disponible";
                const min =
                  ref.valor_minimo == null ? "—" : formatNumber(ref.valor_minimo, { maximumFractionDigits: 4 });
                const max =
                  ref.valor_maximo == null ? "—" : formatNumber(ref.valor_maximo, { maximumFractionDigits: 4 });
                return `${min} – ${max}`;
              },
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar medición de agua" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            mutation.mutate({
              lote_id: Number(values.lote_id),
              parametro_id: Number(values.parametro_id),
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
              valor: Number(values.valor),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {loteId ? (
            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { valueAsNumber: true, required: true })}>
                {lotes.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Parámetro">
            <select className="bf-input" {...form.register("parametro_id", { valueAsNumber: true, required: true })}>
              {parametros.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre} ({row.unidad})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Valor">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              {...form.register("valor", { valueAsNumber: true })}
            />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || parametros.length === 0}>
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
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
