import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { getVenta } from "../../api/finance";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate, formatNumber } from "../../utils/format";

export function VentaDetallePage() {
  const { id } = useParams();
  const ventaId = Number(id);
  const invalid = !Number.isInteger(ventaId) || ventaId <= 0;

  const ventaQuery = useQuery({
    queryKey: ["venta", ventaId],
    queryFn: () => getVenta(ventaId),
    enabled: !invalid,
  });
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });

  if (invalid) {
    return <ErrorAlert message="Identificador de venta inválido." />;
  }
  if (ventaQuery.isLoading) {
    return <LoadingState label="Cargando venta…" />;
  }
  if (ventaQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(ventaQuery.error)} />
        <Link to="/finanzas/ventas" className="bf-btn-secondary inline-flex">
          Volver a ventas
        </Link>
      </div>
    );
  }

  const venta = ventaQuery.data;
  if (!venta) return null;
  const lotes = new Map((lotesQuery.data ?? []).map((row) => [row.id, row]));

  return (
    <div>
      <div className="mb-4">
        <Link to="/finanzas/ventas" className="text-sm text-[var(--bf-accent)]">
          ← Ventas
        </Link>
      </div>
      <div className="rounded-2xl border border-[var(--bf-border)] bg-white p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Venta</p>
        <h1 className="font-display text-3xl font-semibold text-[var(--bf-ink)]">#{venta.id}</h1>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Fecha" value={formatDate(venta.fecha)} />
          <Info label="Cliente" value={venta.cliente || "—"} />
          <Info label="Total (servidor)" value={formatCop(venta.total)} />
          <Info label="Registró" value={`#${venta.registrado_por}`} />
        </dl>
        <p className="mt-3 text-sm text-[var(--bf-muted)]">{venta.observaciones || "Sin observaciones."}</p>
      </div>

      <section className="mt-6">
        <h2 className="mb-1 font-display text-lg font-semibold">Detalle por lote</h2>
        <p className="mb-3 text-sm text-[var(--bf-muted)]">
          El API no declara peso ni producto. Cantidad y subtotal se muestran tal como llegan.
        </p>
        <DataTable
          rows={venta.detalles ?? []}
          rowKey={(row) => row.id}
          empty="Esta venta no tiene líneas."
          columns={[
            {
              key: "lote",
              header: "Lote",
              render: (row) => {
                const lote = lotes.get(row.lote_id);
                return (
                  <Link to={`/produccion/lotes/${row.lote_id}`} className="text-[var(--bf-accent)]">
                    {lote?.codigo ?? `#${row.lote_id}`}
                  </Link>
                );
              },
            },
            {
              key: "cant",
              header: "Cantidad",
              render: (row) => formatNumber(row.cantidad, { maximumFractionDigits: 3 }),
            },
            { key: "pu", header: "Precio unitario", render: (row) => formatCop(row.precio_unitario) },
            { key: "sub", header: "Subtotal", render: (row) => formatCop(row.subtotal) },
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
