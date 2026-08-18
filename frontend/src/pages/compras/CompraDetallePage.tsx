import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { listProductos, listProductosStock, listTiposMovimientoInventario } from "../../api/inventory";
import { getCompra } from "../../api/purchases";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate, formatDateTime, formatNumber } from "../../utils/format";

export function CompraDetallePage() {
  const { id } = useParams();
  const compraId = Number(id);
  const invalid = !Number.isInteger(compraId) || compraId <= 0;

  const compraQuery = useQuery({
    queryKey: ["compra", compraId],
    queryFn: () => getCompra(compraId),
    enabled: !invalid,
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

  if (invalid) {
    return <ErrorAlert message="Identificador de compra inválido." />;
  }
  if (compraQuery.isLoading) {
    return <LoadingState label="Cargando compra…" />;
  }
  if (compraQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(compraQuery.error)} />
        <Link to="/compras" className="bf-btn-secondary inline-flex">
          Volver a compras
        </Link>
      </div>
    );
  }

  const compra = compraQuery.data;
  if (!compra) return null;

  const productos = new Map((productosQuery.data ?? []).map((row) => [row.id, row]));
  const tipos = new Map((tiposQuery.data ?? []).map((row) => [row.id, row]));
  const unidades = new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row.unidad]));

  return (
    <div>
      <div className="mb-4">
        <Link to="/compras" className="text-sm text-[var(--bf-accent)]">
          ← Compras
        </Link>
      </div>
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

      <section className="mt-6">
        <h2 className="mb-3 font-display text-lg font-semibold">Detalle</h2>
        <DataTable
          rows={compra.detalles ?? []}
          rowKey={(row) => row.id}
          empty="Esta compra no tiene líneas."
          columns={[
            {
              key: "producto",
              header: "Producto",
              render: (row) => {
                const producto = productos.get(row.producto_id);
                return producto ? `${producto.codigo} · ${producto.nombre}` : `#${row.producto_id}`;
              },
            },
            {
              key: "cant",
              header: "Cantidad",
              render: (row) => {
                const unidad = unidades.get(row.producto_id);
                return `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })}${unidad ? ` ${unidad}` : ""}`;
              },
            },
            { key: "pu", header: "Precio unitario", render: (row) => formatCop(row.precio_unitario) },
            { key: "sub", header: "Subtotal", render: (row) => formatCop(row.subtotal) },
          ]}
        />
      </section>

      <section className="mt-6">
        <h2 className="mb-1 font-display text-lg font-semibold">Movimientos generados</h2>
        <p className="mb-3 text-sm text-[var(--bf-muted)]">
          Lo que devuelve GET /compras/{compra.id} en el campo movimientos. Referencia DETALLE_COMPRA.
        </p>
        <DataTable
          rows={compra.movimientos ?? []}
          rowKey={(row) => row.id}
          empty="El API no devolvió movimientos asociados a esta compra."
          columns={[
            { key: "id", header: "Movimiento", render: (row) => `#${row.id}` },
            {
              key: "tipo",
              header: "Tipo",
              render: (row) => tipos.get(row.tipo_movimiento_id)?.nombre ?? `#${row.tipo_movimiento_id}`,
            },
            {
              key: "producto",
              header: "Producto",
              render: (row) => {
                const producto = productos.get(row.producto_id);
                return producto ? producto.codigo : `#${row.producto_id}`;
              },
            },
            {
              key: "cant",
              header: "Cantidad",
              render: (row) => formatNumber(row.cantidad, { maximumFractionDigits: 3 }),
            },
            {
              key: "ref",
              header: "Referencia",
              render: (row) =>
                row.referencia_tipo
                  ? `${row.referencia_tipo}${row.referencia_id != null ? ` #${row.referencia_id}` : ""}`
                  : "—",
            },
            {
              key: "fecha",
              header: "Fecha/hora",
              render: (row) => formatDateTime(row.fecha_hora),
            },
          ]}
        />
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{label}</dt>
      <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">{value}</dd>
    </div>
  );
}
