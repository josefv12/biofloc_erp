import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { listProductos, listProductosStock, listTiposMovimientoInventario } from "../../api/inventory";
import { getCompra, updateCompra } from "../../api/purchases";
import { apiErrorMessage } from "../../utils/apiError";
import { etiquetaProducto, formatCop, formatDate, formatDateTime, formatNumber } from "../../utils/format";
import { cantidadDesdePresentacion, cantidadParaPresentacion, precioConUnidad, precioDesdePresentacion, precioParaPresentacion, unidadPresentacion } from "../../utils/unidades";
import { useAuth } from "../../auth/AuthProvider";
import { can } from "../../utils/rbac";
import type { CompraCreate } from "../../types/purchases";

export function CompraDetallePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const compraId = Number(id);
  const invalid = !Number.isInteger(compraId) || compraId <= 0;

  const compraQuery = useQuery({ queryKey: ["compra", compraId], queryFn: () => getCompra(compraId), enabled: !invalid });
  const productosQuery = useQuery({ queryKey: ["productos", { soloActivos: false }], queryFn: () => listProductos({ soloActivos: false }) });
  const tiposQuery = useQuery({ queryKey: ["tipos-movimiento-inventario"], queryFn: listTiposMovimientoInventario });
  const stockQuery = useQuery({ queryKey: ["productos-stock"], queryFn: listProductosStock });
  const updateMutation = useMutation({
    mutationFn: (data: CompraCreate) => updateCompra(compraId, data),
    onSuccess: async () => {
      setEditOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["compra", compraId] }),
        queryClient.invalidateQueries({ queryKey: ["compras"] }),
        queryClient.invalidateQueries({ queryKey: ["movimientos-inventario"] }),
        queryClient.invalidateQueries({ queryKey: ["productos-stock"] }),
      ]);
    },
    onError: (error) => setEditError(apiErrorMessage(error)),
  });

  if (invalid) return <ErrorAlert message="Identificador de compra inválido." />;
  if (compraQuery.isLoading) return <LoadingState label="Cargando compra…" />;
  if (compraQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(compraQuery.error)} />
        <Link to="/compras" className="bf-btn-secondary inline-flex">Volver a compras</Link>
      </div>
    );
  }

  const compra = compraQuery.data;
  if (!compra) return null;
  const puedeEditar = can(user?.rol, "registrarCompra");

  const productos = new Map((productosQuery.data ?? []).map((row) => [row.id, row]));
  const tipos = new Map((tiposQuery.data ?? []).map((row) => [row.id, row]));
  const stock = new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row]));

  return (
    <div>
      <div className="mb-4"><Link to="/compras" className="text-sm text-[var(--bf-accent)]">← Compras</Link></div>
      <div className="rounded-2xl border border-[var(--bf-border)] bg-white p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Compra</p>
        <h1 className="font-display text-3xl font-semibold text-[var(--bf-ink)]">#{compra.id}</h1>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Fecha" value={formatDate(compra.fecha)} />
          <Info label="Proveedor" value={compra.proveedor || "—"} />
          <Info label="Total (servidor)" value={formatCop(compra.total)} />
          <Info label="Registró" value={`#${compra.registrado_por}`} />
        </dl>
        <p className="mt-3 text-sm text-[var(--bf-muted)]">{compra.observaciones || "Sin observaciones."}</p>
      </div>

      <div className="mt-4 flex justify-end">{puedeEditar ? <button type="button" className="bf-btn-primary" onClick={() => { setEditError(null); setEditOpen(true); }}>Editar compra</button> : null}</div>

      <section className="mt-6">
        <h2 className="mb-3 font-display text-lg font-semibold">Detalle</h2>
        <DataTable
          rows={compra.detalles ?? []}
          rowKey={(row) => row.id}
          empty="Esta compra no tiene líneas."
          columns={[
            { key: "producto", header: "Producto", render: (row) => {
              const producto = productos.get(row.producto_id);
              return producto ? etiquetaProducto(producto.nombre, producto.codigo) : `#${row.producto_id}`;
            }},
            { key: "cant", header: "Cantidad", render: (row) => {
              const productoStock = stock.get(row.producto_id);
              const unidad = productoStock?.unidad;
              const comercial = productoStock?.unidad_comercial;
              return `${formatNumber(cantidadParaPresentacion(row.cantidad, unidad, productoStock?.factor_conversion), { maximumFractionDigits: 3 })}${unidad ? ` ${unidadPresentacion(unidad, comercial)}` : ""}`;
            }},
            { key: "pu", header: "Precio unitario", render: (row) => {
              const productoStock = stock.get(row.producto_id);
              return precioConUnidad(row.precio_unitario, productoStock?.unidad, productoStock?.factor_conversion, productoStock?.unidad_comercial);
            }},
            { key: "sub", header: "Subtotal", render: (row) => formatCop(row.subtotal) },
          ]}
        />
      </section>

      <section className="mt-6">
        <h2 className="mb-1 font-display text-lg font-semibold">Movimientos generados</h2>
        <p className="mb-3 text-sm text-[var(--bf-muted)]">Lo que devuelve GET /compras/{compra.id} en el campo movimientos. Referencia DETALLE_COMPRA.</p>
        <DataTable
          rows={compra.movimientos ?? []}
          rowKey={(row) => row.id}
          empty="El API no devolvió movimientos asociados a esta compra."
          columns={[
            { key: "id", header: "Movimiento", render: (row) => `#${row.id}` },
            { key: "tipo", header: "Tipo", render: (row) => tipos.get(row.tipo_movimiento_id)?.nombre ?? `#${row.tipo_movimiento_id}` },
            { key: "producto", header: "Producto", render: (row) => productos.get(row.producto_id)?.codigo ?? `#${row.producto_id}` },
            { key: "cant", header: "Cantidad", render: (row) => {
              const productoStock = stock.get(row.producto_id);
              const unidad = productoStock?.unidad;
              const comercial = productoStock?.unidad_comercial;
              return `${formatNumber(cantidadParaPresentacion(row.cantidad, unidad, productoStock?.factor_conversion), { maximumFractionDigits: 3 })}${unidad ? ` ${unidadPresentacion(unidad, comercial)}` : ""}`;
            }},
            { key: "ref", header: "Referencia", render: (row) => row.referencia_tipo ? `${row.referencia_tipo}${row.referencia_id != null ? ` #${row.referencia_id}` : ""}` : "—" },
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
          ]}
        />
      </section>

      <Modal open={editOpen} title={`Editar compra #${compra.id}`} size="lg" onClose={() => setEditOpen(false)}>
        <form className="space-y-4" onSubmit={(event) => {
          event.preventDefault();
          setEditError(null);
          const form = event.currentTarget;
          const fecha = (form.elements.namedItem("edit_fecha") as HTMLInputElement).value;
          const proveedor = (form.elements.namedItem("edit_proveedor") as HTMLInputElement).value.trim();
          const observaciones = (form.elements.namedItem("edit_observaciones") as HTMLTextAreaElement).value.trim();
          const detalles: CompraCreate["detalles"] = compra.detalles.map((detalle) => {
            const cantidadPresentada = Number((form.elements.namedItem(`cantidad_${detalle.id}`) as HTMLInputElement).value);
            const precioPresentado = Number((form.elements.namedItem(`precio_${detalle.id}`) as HTMLInputElement).value);
            const productoStock = stock.get(detalle.producto_id);
            const simboloInterno = productoStock?.unidad ?? null;
            const factor = productoStock?.factor_conversion;
            return {
              producto_id: detalle.producto_id,
              cantidad: cantidadDesdePresentacion(cantidadPresentada, simboloInterno, factor),
              precio_unitario: precioDesdePresentacion(precioPresentado, simboloInterno, factor),
            };
          });
          if (!fecha || detalles.some((d) => !Number.isFinite(d.cantidad) || d.cantidad <= 0 || !Number.isFinite(d.precio_unitario) || d.precio_unitario < 0)) {
            setEditError("Revisa fecha, cantidades y precios.");
            return;
          }
          updateMutation.mutate({ fecha, proveedor: proveedor || null, observaciones: observaciones || null, detalles });
        }}>
          {editError ? <ErrorAlert message={editError} /> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm"><span className="mb-1 block font-medium">Fecha</span><input name="edit_fecha" type="date" className="bf-input" defaultValue={compra.fecha} required /></label>
            <label className="block text-sm"><span className="mb-1 block font-medium">Proveedor</span><input name="edit_proveedor" className="bf-input" defaultValue={compra.proveedor ?? ""} /></label>
          </div>
          <div className="space-y-3">
            {compra.detalles.map((detalle) => {
              const producto = productos.get(detalle.producto_id);
              const productoStock = stock.get(detalle.producto_id);
              const unidad = productoStock?.unidad;
              const comercial = productoStock?.unidad_comercial;
              const unidadMostrar = unidadPresentacion(unidad, comercial);
              const cantidadMostrar = cantidadParaPresentacion(detalle.cantidad, unidad, productoStock?.factor_conversion);
              const precioMostrar = precioParaPresentacion(detalle.precio_unitario, unidad, productoStock?.factor_conversion);
              return <div key={detalle.id} className="rounded-lg border border-[var(--bf-border)] p-3">
                <p className="mb-3 text-sm font-medium">{producto ? etiquetaProducto(producto.nombre, producto.codigo) : `#${detalle.producto_id}`}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block text-sm"><span className="mb-1 block">Cantidad {unidadMostrar ? `(${unidadMostrar})` : ""}</span><input name={`cantidad_${detalle.id}`} type="number" step="any" min="0.0001" className="bf-input" defaultValue={cantidadMostrar} /></label>
                  <label className="block text-sm"><span className="mb-1 block">Precio unitario {unidadMostrar ? `($ / ${unidadMostrar})` : ""}</span><input name={`precio_${detalle.id}`} type="number" step="any" min="0" className="bf-input" defaultValue={precioMostrar} /></label>
                </div>
              </div>;
            })}
          </div>
          <label className="block text-sm"><span className="mb-1 block font-medium">Observaciones</span><textarea name="edit_observaciones" className="bf-input min-h-20" defaultValue={compra.observaciones ?? ""} /></label>
          <p className="text-xs text-[var(--bf-muted)]">La edición conserva los productos y líneas originales. Si existen consumos posteriores, el sistema revalora sus costos para mantener consistencia.</p>
          <button type="submit" className="bf-btn-primary" disabled={updateMutation.isPending}>{updateMutation.isPending ? "Guardando…" : "Guardar cambios"}</button>
        </form>
      </Modal>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{label}</dt><dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">{value}</dd></div>;
}
