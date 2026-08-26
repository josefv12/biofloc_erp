import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { ContextoAlimentacionPanel } from "../../components/alimentacion/ContextoAlimentacionPanel";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import { createAlimentacion, listAlimentaciones, listProductosActivos, listUnidades } from "../../api/operations";
import { getContextoAlimentacionLote } from "../../api/alimentacionReferencia";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import {
  etiquetaProducto,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
  withFechaHoraIso,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import { esLoteActivo, lotesActivos } from "../../utils/loteEstado";
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
  const enProduccion = lotesActivos(lotes);
  const loteContexto = loteId ? lotes.find((row) => row.id === loteId) : undefined;
  const puedeRegistrarLote = !loteId || esLoteActivo(loteContexto);
  const form = useForm({
    defaultValues: {
      lote_id: loteId ?? 0,
      producto_id: 0,
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      observaciones: "",
    },
  });
  const loteFormId = form.watch("lote_id") || loteId;
  const productoFormId = form.watch("producto_id");
  const productoSeleccionado = productos.get(Number(productoFormId));
  const simboloUnidad = productoSeleccionado
    ? unidades.get(productoSeleccionado.unidad_id)?.simbolo
    : undefined;
  const etiquetaCantidad = simboloUnidad
    ? `Cantidad suministrada (${simboloUnidad})`
    : "Cantidad suministrada";
  const contextoQuery = useQuery({
    queryKey: ["contexto-alimentacion", loteFormId],
    queryFn: () => getContextoAlimentacionLote(Number(loteFormId)),
    enabled: open && Boolean(loteFormId),
  });
  const ref = contextoQuery.data?.referencia_activa;
  const [stockMsg, setStockMsg] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (data: AlimentacionCreate) => createAlimentacion(data),
    onSuccess: async (resp) => {
      setOpen(false);
      if (resp.stock_restante != null) {
        setStockMsg(`Inventario actualizado: ${resp.stock_restante.toFixed(2)} disponibles`);
        setTimeout(() => setStockMsg(null), 6000);
      }
      await queryClient.invalidateQueries({ queryKey: ["alimentaciones"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] });
      await queryClient.invalidateQueries({ queryKey: ["contexto-alimentacion"] });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });
  const rows = compact ? (query.data ?? []).slice(0, 5) : (query.data ?? []);

  return (
    <div>
      {stockMsg ? (
        <div className="mb-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {stockMsg}
        </div>
      ) : null}
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
          {can(user?.rol, "registrarAlimentacion") && puedeRegistrarLote ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  lote_id: loteId ?? enProduccion[0]?.id ?? 0,
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
                return producto ? etiquetaProducto(producto.nombre, producto.codigo) : `#${row.producto_id}`;
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
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            mutation.mutate({
              lote_id: Number(values.lote_id),
              producto_id: Number(values.producto_id),
              fecha_hora: fechaHora,
              cantidad: Number(values.cantidad),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {contextoQuery.isLoading ? (
            <p className="text-sm text-[var(--bf-muted)]">Calculando ración recomendada…</p>
          ) : ref ? (
            <ContextoAlimentacionPanel ref={ref} />
          ) : contextoQuery.isSuccess ? (
            <p className="text-sm text-[var(--bf-muted)]">N/D — Sin referencia configurada.</p>
          ) : null}
          {loteId ? (
            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { valueAsNumber: true })}>
                {enProduccion.map((row) => (
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
                  {etiquetaProducto(row.nombre, row.codigo)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label={etiquetaCantidad}>
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
            El inventario se actualizará automáticamente al registrar.
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
