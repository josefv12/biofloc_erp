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
  createAlimentacion,
  listAlimentaciones,
  listProductosActivos,
  listUnidades,
} from "../../api/operations";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import {
  datetimeLocalToIso,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Alimentacion, AlimentacionCreate, Producto, Unidad } from "../../types/operations";
import type { Lote } from "../../types/production";

export function AlimentacionPage() {
  const [params, setParams] = useSearchParams();
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });

  return (
    <div>
      <PageHeader
        title="Alimentación"
        description="Registro de alimento por lote. No descuenta inventario ni crea movimientos."
      />
      <label className="mb-4 block max-w-xs text-sm">
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
      <AlimentacionPanel loteId={loteId} lotes={lotesQuery.data ?? []} compact={false} />
    </div>
  );
}

export function AlimentacionPanel({
  loteId,
  lotes,
  compact,
}: {
  loteId?: number;
  lotes: Lote[];
  compact: boolean;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["alimentaciones", loteId],
    queryFn: () => listAlimentaciones(loteId),
  });
  const productosQuery = useQuery({ queryKey: ["productos-activos"], queryFn: listProductosActivos });
  const unidadesQuery = useQuery({ queryKey: ["unidades"], queryFn: listUnidades });
  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((row: Producto) => [row.id, row])),
    [productosQuery.data],
  );
  const unidades = useMemo(
    () => new Map((unidadesQuery.data ?? []).map((row: Unidad) => [row.id, row])),
    [unidadesQuery.data],
  );
  const lotesMap = useMemo(() => new Map(lotes.map((row) => [row.id, row])), [lotes]);
  const form = useForm({
    defaultValues: {
      lote_id: loteId ?? 0,
      producto_id: 0,
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      observaciones: "",
    },
  });
  const mutation = useMutation({
    mutationFn: (data: AlimentacionCreate) => createAlimentacion(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["alimentaciones"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });
  const rows = compact ? (query.data ?? []).slice(0, 5) : (query.data ?? []);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-[var(--bf-muted)]">
          {compact ? "Últimas alimentaciones de este lote" : "Historial de alimentación"}
        </p>
        <div className="flex gap-2">
          {compact && loteId ? (
            <Link to={`/operacion/alimentacion?lote_id=${loteId}`} className="bf-btn-secondary">
              Ver todas
            </Link>
          ) : null}
          {can(user?.rol, "registrarAlimentacion") ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  lote_id: loteId ?? lotes[0]?.id ?? 0,
                  producto_id: productosQuery.data?.[0]?.id ?? 0,
                  fecha_hora: toDatetimeLocalValue(),
                  cantidad: "",
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar alimentación
            </button>
          ) : null}
        </div>
      </div>
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={rows}
          rowKey={(row: Alimentacion) => row.id}
          empty="No hay alimentaciones."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            ...(!loteId
              ? [
                  {
                    key: "lote",
                    header: "Lote",
                    render: (row: Alimentacion) => lotesMap.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
                  },
                ]
              : []),
            {
              key: "producto",
              header: "Producto",
              render: (row) => {
                const producto = productos.get(row.producto_id);
                return producto ? `${producto.codigo} · ${producto.nombre}` : `#${row.producto_id}`;
              },
            },
            {
              key: "cantidad",
              header: "Cantidad",
              render: (row) => {
                const producto = productos.get(row.producto_id);
                const simbolo = producto ? unidades.get(producto.unidad_id)?.simbolo : undefined;
                return `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })}${simbolo ? ` ${simbolo}` : ""}`;
              },
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar alimentación" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            mutation.mutate({
              lote_id: Number(values.lote_id),
              producto_id: Number(values.producto_id),
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
              cantidad: Number(values.cantidad),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {loteId ? (
            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { valueAsNumber: true })}>
                {lotes.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Producto">
            <select className="bf-input" {...form.register("producto_id", { valueAsNumber: true })}>
              {(productosQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.codigo} · {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Cantidad">
            <input
              type="number"
              step="any"
              min="0.0001"
              className="bf-input"
              {...form.register("cantidad", { valueAsNumber: true })}
            />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            No se descuenta stock. No se llama a POST /movimientos-inventario.
          </p>
          <button
            type="submit"
            className="bf-btn-primary"
            disabled={mutation.isPending || (productosQuery.data ?? []).length === 0}
          >
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
