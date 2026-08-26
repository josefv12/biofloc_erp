import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import { listProductos, listProductosStock } from "../../api/inventory";
import { createCompra, listCompras } from "../../api/purchases";
import { apiErrorMessage } from "../../utils/apiError";
import { etiquetaProducto, formatCop, formatDate, formatNumber } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Compra, CompraCreate, DetalleCompraIn } from "../../types/purchases";

type Linea = {
  key: string;
  producto_id: string;
  cantidad: string;
  precio_unitario: string;
};

function todayDateInput(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function newLinea(): Linea {
  return { key: crypto.randomUUID(), producto_id: "", cantidad: "", precio_unitario: "" };
}

export function ComprasPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fecha, setFecha] = useState(todayDateInput());
  const [proveedor, setProveedor] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [lineas, setLineas] = useState<Linea[]>([newLinea()]);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const puedeRegistrar = can(user?.rol, "registrarCompra");

  const comprasQuery = useQuery({
    queryKey: ["compras", fechaDesde, fechaHasta],
    queryFn: () =>
      listCompras({
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
      }),
  });
  const productosQuery = useQuery({
    queryKey: ["productos", { soloActivos: true }],
    queryFn: () => listProductos({ soloActivos: true }),
  });
  const stockQuery = useQuery({ queryKey: ["productos-stock"], queryFn: listProductosStock });

  const unidades = useMemo(
    () => new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row.unidad])),
    [stockQuery.data],
  );

  const mutation = useMutation({
    mutationFn: (data: CompraCreate) => createCompra(data),
    onSuccess: async (compra) => {
      setOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["compras"] }),
        queryClient.invalidateQueries({ queryKey: ["movimientos-inventario"] }),
        queryClient.invalidateQueries({ queryKey: ["productos-stock"] }),
        queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo"] }),
        queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo-seccion"] }),
      ]);
      navigate(`/compras/${compra.id}`);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    setFecha(todayDateInput());
    setProveedor("");
    setObservaciones("");
    const first = productosQuery.data?.[0];
    setLineas([
      {
        key: crypto.randomUUID(),
        producto_id: first ? String(first.id) : "",
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
        title="Compras"
        description="Registrar una compra genera automáticamente la entrada de inventario. No se llama a movimientos desde esta pantalla."
        actions={
          puedeRegistrar ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Nueva compra
            </button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Desde</span>
          <input type="date" className="bf-input" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Hasta</span>
          <input type="date" className="bf-input" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
        </label>
      </div>

      {comprasQuery.isLoading ? <LoadingState /> : null}
      {comprasQuery.isError ? <ErrorAlert message={apiErrorMessage(comprasQuery.error)} /> : null}
      {comprasQuery.data ? (
        <DataTable
          rows={comprasQuery.data}
          rowKey={(row: Compra) => row.id}
          empty="No hay compras."
          onRowClick={(row) => navigate(`/compras/${row.id}`)}
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDate(row.fecha) },
            { key: "proveedor", header: "Proveedor", render: (row) => row.proveedor || "—" },
            {
              key: "lineas",
              header: "Líneas",
              render: (row) => formatNumber(row.detalles?.length ?? 0),
            },
            { key: "total", header: "Total", render: (row) => formatCop(row.total) },
            { key: "usuario", header: "Registró", render: (row) => `#${row.registrado_por}` },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
            {
              key: "ver",
              header: "",
              render: (row) => (
                <Link to={`/compras/${row.id}`} className="text-sm text-[var(--bf-accent)]" onClick={(e) => e.stopPropagation()}>
                  Ver detalle
                </Link>
              ),
            },
          ]}
        />
      ) : null}

      <Modal open={open} title="Nueva compra" size="lg" onClose={() => setOpen(false)}>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const detalles: DetalleCompraIn[] = [];
            for (const linea of lineas) {
              const producto_id = Number(linea.producto_id);
              const cantidad = Number(linea.cantidad);
              const precio_unitario = Number(linea.precio_unitario);
              if (!producto_id || !Number.isFinite(cantidad) || !Number.isFinite(precio_unitario)) {
                setFormError("Cada línea requiere producto, cantidad y precio unitario.");
                return;
              }
              detalles.push({ producto_id, cantidad, precio_unitario });
            }
            mutation.mutate({
              fecha,
              proveedor: proveedor.trim() || null,
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
            <Field label="Proveedor (opcional)">
              <input className="bf-input" value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
            </Field>
          </div>
          <div className="space-y-3">
            <p className="text-sm font-medium text-[var(--bf-ink)]">Productos</p>
            {lineas.map((linea, index) => {
              const productoId = Number(linea.producto_id) || undefined;
              const unidad = productoId ? unidades.get(productoId) : undefined;
              const cantidad = Number(linea.cantidad);
              const precio = Number(linea.precio_unitario);
              const subtotal =
                Number.isFinite(cantidad) && Number.isFinite(precio) ? cantidad * precio : null;
              return (
                <div key={linea.key} className="rounded-lg border border-[var(--bf-border)] p-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Producto">
                      <select
                        className="bf-input"
                        value={linea.producto_id}
                        onChange={(e) =>
                          setLineas((rows) =>
                            rows.map((row) =>
                              row.key === linea.key ? { ...row, producto_id: e.target.value } : row,
                            ),
                          )
                        }
                      >
                        <option value="">Seleccione</option>
                        {(productosQuery.data ?? []).map((row) => (
                          <option key={row.id} value={row.id}>
                            {etiquetaProducto(row.nombre, row.codigo)}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label={`Cantidad${unidad ? ` (${unidad})` : ""}`}>
                      <input
                        type="number"
                        step="any"
                        min="0.001"
                        className="bf-input"
                        value={linea.cantidad}
                        onChange={(e) =>
                          setLineas((rows) =>
                            rows.map((row) =>
                              row.key === linea.key ? { ...row, cantidad: e.target.value } : row,
                            ),
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
                      <p className="rounded-md bg-[var(--bf-chip)] px-3 py-2">
                        {subtotal == null ? "—" : formatCop(subtotal)}
                      </p>
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
                    producto_id: productosQuery.data?.[0] ? String(productosQuery.data[0].id) : "",
                    cantidad: "",
                    precio_unitario: "",
                  },
                ])
              }
            >
              Agregar producto
            </button>
          </div>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
          </Field>
          <div className="rounded-lg bg-[var(--bf-chip)] px-3 py-3 text-sm">
            <p className="text-[var(--bf-muted)]">Suma visual de líneas (no sustituye el total del servidor)</p>
            <p className="mt-1 font-display text-xl font-semibold">{formatCop(ayudaVisual)}</p>
          </div>
          <button
            type="submit"
            className="bf-btn-primary"
            disabled={mutation.isPending || (productosQuery.data ?? []).length === 0}
          >
            {mutation.isPending ? "Guardando…" : "Registrar compra"}
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
