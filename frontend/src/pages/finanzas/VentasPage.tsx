import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import { createVenta, listVentas } from "../../api/finance";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate, formatNumber } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { DetalleVentaCreate, Venta, VentaCreate } from "../../types/finance";

type Linea = {
  key: string;
  lote_id: string;
  cantidad: string;
  precio_unitario: string;
};

function todayDateInput(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function VentasPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const fechaDesde = params.get("fecha_desde") ?? "";
  const fechaHasta = params.get("fecha_hasta") ?? "";
  const cliente = params.get("cliente") ?? "";
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fecha, setFecha] = useState(todayDateInput());
  const [clienteForm, setClienteForm] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [lineas, setLineas] = useState<Linea[]>([]);
  const puedeRegistrar = can(user?.rol, "registrarVenta");

  const ventasQuery = useQuery({
    queryKey: ["ventas", loteId, fechaDesde, fechaHasta, cliente],
    queryFn: () =>
      listVentas({
        loteId,
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
        cliente: cliente || undefined,
      }),
  });
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const lotes = useMemo(() => new Map((lotesQuery.data ?? []).map((row) => [row.id, row])), [lotesQuery.data]);

  const mutation = useMutation({
    mutationFn: (data: VentaCreate) => createVenta(data),
    onSuccess: async (venta) => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["ventas"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      navigate(`/finanzas/ventas/${venta.id}`);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function openCreate() {
    setFormError(null);
    setFecha(todayDateInput());
    setClienteForm("");
    setObservaciones("");
    setLineas([
      {
        key: crypto.randomUUID(),
        lote_id: loteId ? String(loteId) : String(lotesQuery.data?.[0]?.id ?? ""),
        cantidad: "",
        precio_unitario: "",
      },
    ]);
    setOpen(true);
  }

  const ayudaVisual = lineas.reduce((acc, linea) => {
    const cantidad = Number(linea.cantidad);
    const precio = Number(linea.precio_unitario);
    if (!Number.isFinite(cantidad) || !Number.isFinite(precio)) return acc;
    return acc + cantidad * precio;
  }, 0);

  return (
    <div>
      <PageHeader
        title="Ventas"
        description="La venta se asocia a lotes, no a productos. No descuenta inventario. El total lo confirma el servidor."
        actions={
          puedeRegistrar ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Registrar venta
            </button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Desde</span>
          <input type="date" className="bf-input" value={fechaDesde} onChange={(e) => setParam("fecha_desde", e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Hasta</span>
          <input type="date" className="bf-input" value={fechaHasta} onChange={(e) => setParam("fecha_hasta", e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Lote</span>
          <select className="bf-input" value={loteId ?? ""} onChange={(e) => setParam("lote_id", e.target.value)}>
            <option value="">Todos</option>
            {(lotesQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.codigo}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Cliente</span>
          <input className="bf-input" value={cliente} onChange={(e) => setParam("cliente", e.target.value)} />
        </label>
      </div>

      {ventasQuery.isLoading ? <LoadingState /> : null}
      {ventasQuery.isError ? <ErrorAlert message={apiErrorMessage(ventasQuery.error)} /> : null}
      {ventasQuery.data ? (
        <DataTable
          rows={ventasQuery.data}
          rowKey={(row: Venta) => row.id}
          empty="No hay ventas."
          onRowClick={(row) => navigate(`/finanzas/ventas/${row.id}`)}
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDate(row.fecha) },
            { key: "cliente", header: "Cliente", render: (row) => row.cliente || "—" },
            {
              key: "lotes",
              header: "Lotes",
              render: (row) =>
                (row.detalles ?? [])
                  .map((detalle) => lotes.get(detalle.lote_id)?.codigo ?? `#${detalle.lote_id}`)
                  .join(", ") || "—",
            },
            { key: "lineas", header: "Líneas", render: (row) => formatNumber(row.detalles?.length ?? 0) },
            { key: "total", header: "Total", render: (row) => formatCop(row.total) },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
            {
              key: "ver",
              header: "",
              render: (row) => (
                <Link
                  to={`/finanzas/ventas/${row.id}`}
                  className="text-sm text-[var(--bf-accent)]"
                  onClick={(e) => e.stopPropagation()}
                >
                  Ver detalle
                </Link>
              ),
            },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar venta" size="lg" onClose={() => setOpen(false)}>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const detalles: DetalleVentaCreate[] = [];
            for (const linea of lineas) {
              const lote_id = Number(linea.lote_id);
              const cantidad = Number(linea.cantidad);
              const precio_unitario = Number(linea.precio_unitario);
              if (!lote_id || !Number.isFinite(cantidad) || !Number.isFinite(precio_unitario)) {
                setFormError("Cada línea requiere lote, cantidad y precio unitario.");
                return;
              }
              detalles.push({ lote_id, cantidad, precio_unitario });
            }
            mutation.mutate({
              fecha,
              cliente: clienteForm.trim() || null,
              observaciones: observaciones.trim() || null,
              detalles,
            });
          }}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Fecha">
              <input type="date" className="bf-input" required value={fecha} onChange={(e) => setFecha(e.target.value)} />
            </Field>
            <Field label="Cliente (opcional)">
              <input className="bf-input" value={clienteForm} onChange={(e) => setClienteForm(e.target.value)} />
            </Field>
          </div>
          <div className="space-y-3">
            <p className="text-sm font-medium text-[var(--bf-ink)]">Líneas por lote</p>
            {lineas.map((linea, index) => {
              const cantidad = Number(linea.cantidad);
              const precio = Number(linea.precio_unitario);
              const subtotal = Number.isFinite(cantidad) && Number.isFinite(precio) ? cantidad * precio : null;
              return (
                <div key={linea.key} className="rounded-lg border border-[var(--bf-border)] p-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Lote">
                      <select
                        className="bf-input"
                        value={linea.lote_id}
                        onChange={(e) =>
                          setLineas((rows) =>
                            rows.map((row) => (row.key === linea.key ? { ...row, lote_id: e.target.value } : row)),
                          )
                        }
                      >
                        <option value="">Seleccione</option>
                        {(lotesQuery.data ?? []).map((row) => (
                          <option key={row.id} value={row.id}>
                            {row.codigo}
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
                        value={linea.cantidad}
                        onChange={(e) =>
                          setLineas((rows) =>
                            rows.map((row) => (row.key === linea.key ? { ...row, cantidad: e.target.value } : row)),
                          )
                        }
                      />
                    </Field>
                    <Field label="Precio unitario">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        className="bf-input"
                        value={linea.precio_unitario}
                        onChange={(e) =>
                          setLineas((rows) =>
                            rows.map((row) =>
                              row.key === linea.key ? { ...row, precio_unitario: e.target.value } : row,
                            ),
                          )
                        }
                      />
                    </Field>
                    <div className="text-sm">
                      <p className="mb-1 font-medium text-[var(--bf-ink)]">Subtotal (ayuda visual)</p>
                      <p className="rounded-md bg-[var(--bf-chip)] px-3 py-2">{subtotal == null ? "—" : formatCop(subtotal)}</p>
                    </div>
                  </div>
                  {lineas.length > 1 ? (
                    <button
                      type="button"
                      className="bf-btn-secondary mt-3 !py-1 text-xs"
                      onClick={() => setLineas((rows) => rows.filter((row) => row.key !== linea.key))}
                    >
                      Quitar línea {index + 1}
                    </button>
                  ) : null}
                </div>
              );
            })}
            <button
              type="button"
              className="bf-btn-secondary"
              onClick={() =>
                setLineas((rows) => [
                  ...rows,
                  {
                    key: crypto.randomUUID(),
                    lote_id: String(lotesQuery.data?.[0]?.id ?? ""),
                    cantidad: "",
                    precio_unitario: "",
                  },
                ])
              }
            >
              Agregar lote
            </button>
          </div>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
          </Field>
          <div className="rounded-lg bg-[var(--bf-chip)] px-3 py-3 text-sm">
            <p className="text-[var(--bf-muted)]">Suma visual de líneas (el total oficial lo calcula el servidor)</p>
            <p className="mt-1 font-display text-xl font-semibold">{formatCop(ayudaVisual)}</p>
          </div>
          <p className="text-xs text-[var(--bf-muted)]">
            Esta venta no llama a movimientos de inventario ni descuenta stock.
          </p>
          <button
            type="submit"
            className="bf-btn-primary"
            disabled={mutation.isPending || (lotesQuery.data ?? []).length === 0}
          >
            {mutation.isPending ? "Guardando…" : "Registrar venta"}
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
