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
  createMovimientoInventario,
  listMovimientosInventario,
  listProductos,
  listProductosStock,
  listTiposMovimientoInventario,
} from "../../api/inventory";
import { apiErrorMessage } from "../../utils/apiError";
import {
  datetimeLocalToIso,
  formatCop,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import type { MovimientoInventario, MovimientoInventarioCreate } from "../../types/inventory";

type MovimientoForm = {
  producto_id: number;
  tipo_movimiento_id: number;
  cantidad: number;
  fecha_hora: string;
  referencia_tipo: string;
  referencia_id: string;
  observaciones: string;
  costo_unitario: string;
  costo_total: string;
};

export function MovimientosPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const productoId = Number(params.get("producto_id") ?? "") || undefined;
  const tipoId = Number(params.get("tipo_id") ?? "") || undefined;
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarMovimiento");

  const movimientosQuery = useQuery({
    queryKey: ["movimientos-inventario", productoId, tipoId],
    queryFn: () => listMovimientosInventario({ productoId, tipoMovimientoId: tipoId }),
  });
  const productosQuery = useQuery({
    queryKey: ["productos", { soloActivos: false }],
    queryFn: () => listProductos({ soloActivos: false }),
  });
  const tiposQuery = useQuery({
    queryKey: ["tipos-movimiento-inventario"],
    queryFn: listTiposMovimientoInventario,
  });
  const stockQuery = useQuery({ queryKey: ["productos-stock"], queryFn: listProductosStock });

  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((row) => [row.id, row])),
    [productosQuery.data],
  );
  const tipos = useMemo(() => new Map((tiposQuery.data ?? []).map((row) => [row.id, row])), [tiposQuery.data]);
  const stock = useMemo(
    () => new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row])),
    [stockQuery.data],
  );

  const form = useForm<MovimientoForm>();
  const mutation = useMutation({
    mutationFn: (data: MovimientoInventarioCreate) => createMovimientoInventario(data),
    onSuccess: async () => {
      setOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["movimientos-inventario"] }),
        queryClient.invalidateQueries({ queryKey: ["productos-stock"] }),
        queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo"] }),
        queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo-seccion"] }),
      ]);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      producto_id: productoId ?? productosQuery.data?.[0]?.id ?? 0,
      tipo_movimiento_id: tiposQuery.data?.[0]?.id ?? 0,
      cantidad: 0.001,
      fecha_hora: toDatetimeLocalValue(),
      referencia_tipo: "",
      referencia_id: "",
      observaciones: "",
      costo_unitario: "",
      costo_total: "",
    });
    setOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Movimientos de inventario"
        description="Histórico inmutable. Una compra ya genera su ENTRADA: no registre otra entrada por la misma compra."
        actions={
          puedeRegistrar ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Registrar movimiento
            </button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Producto</span>
          <select
            className="bf-input"
            value={productoId ?? ""}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("producto_id", event.target.value);
              else next.delete("producto_id");
              setParams(next);
            }}
          >
            <option value="">Todos</option>
            {(productosQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.codigo} · {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Tipo</span>
          <select
            className="bf-input"
            value={tipoId ?? ""}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("tipo_id", event.target.value);
              else next.delete("tipo_id");
              setParams(next);
            }}
          >
            <option value="">Todos</option>
            {(tiposQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <Link to="/inventario" className="bf-btn-secondary self-end">
          Volver a stock
        </Link>
      </div>

      {movimientosQuery.isLoading ? <LoadingState /> : null}
      {movimientosQuery.isError ? <ErrorAlert message={apiErrorMessage(movimientosQuery.error)} /> : null}
      {movimientosQuery.data ? (
        <DataTable
          rows={movimientosQuery.data}
          rowKey={(row: MovimientoInventario) => row.id}
          empty="No hay movimientos."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "producto",
              header: "Producto",
              render: (row) => {
                const producto = productos.get(row.producto_id);
                return producto ? `${producto.codigo} · ${producto.nombre}` : `#${row.producto_id}`;
              },
            },
            {
              key: "tipo",
              header: "Tipo",
              render: (row) => tipos.get(row.tipo_movimiento_id)?.nombre ?? `#${row.tipo_movimiento_id}`,
            },
            {
              key: "cantidad",
              header: "Cantidad",
              render: (row) => {
                const unidad = stock.get(row.producto_id)?.unidad;
                return `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })}${unidad ? ` ${unidad}` : ""}`;
              },
            },
            {
              key: "ref",
              header: "Referencia",
              render: (row) =>
                row.referencia_tipo
                  ? `${row.referencia_tipo}${row.referencia_id != null ? ` #${row.referencia_id}` : ""}`
                  : "—",
            },
            { key: "usuario", header: "Usuario", render: (row) => `#${row.registrado_por}` },
            {
              key: "costo",
              header: "Costo total",
              render: (row) => (row.costo_total == null ? "—" : formatCop(row.costo_total)),
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar movimiento" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const refId = values.referencia_id.trim();
            const cu = values.costo_unitario.trim();
            const ct = values.costo_total.trim();
            mutation.mutate({
              producto_id: Number(values.producto_id),
              tipo_movimiento_id: Number(values.tipo_movimiento_id),
              cantidad: Number(values.cantidad),
              fecha_hora: values.fecha_hora ? datetimeLocalToIso(values.fecha_hora) : null,
              referencia_tipo: values.referencia_tipo.trim() || null,
              referencia_id: refId === "" ? null : Number(refId),
              observaciones: values.observaciones.trim() || null,
              costo_unitario: cu === "" ? null : Number(cu),
              costo_total: ct === "" ? null : Number(ct),
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Producto">
            <select className="bf-input" {...form.register("producto_id", { valueAsNumber: true })}>
              {(productosQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.codigo} · {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tipo de movimiento">
            <select className="bf-input" {...form.register("tipo_movimiento_id", { valueAsNumber: true })}>
              {(tiposQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre} ({row.afecta_stock === 1 ? "suma stock" : "resta stock"})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Cantidad">
            <input
              type="number"
              step="any"
              min="0.001"
              className="bf-input"
              {...form.register("cantidad", { valueAsNumber: true })}
            />
          </Field>
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora")} />
          </Field>
          <Field label="Referencia tipo (opcional)">
            <input className="bf-input" {...form.register("referencia_tipo")} />
          </Field>
          <Field label="Referencia id (opcional)">
            <input type="number" className="bf-input" {...form.register("referencia_id")} />
          </Field>
          <Field label="Costo unitario (opcional)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("costo_unitario")} />
          </Field>
          <Field label="Costo total (opcional)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("costo_total")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            No use este formulario para duplicar la entrada de una compra. El backend ya la crea.
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
