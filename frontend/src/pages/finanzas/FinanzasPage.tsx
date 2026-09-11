import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboardFinanzas } from "../../api/dashboard";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../components/PageHeader";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatNumber } from "../../utils/format";

function validRange(desde: string, hasta: string) {
  return !desde || !hasta || desde <= hasta;
}

export function FinanzasPage() {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [appliedDesde, setAppliedDesde] = useState("");
  const [appliedHasta, setAppliedHasta] = useState("");
  const [rangeError, setRangeError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["dashboard", "finanzas", appliedDesde, appliedHasta],
    queryFn: () => fetchDashboardFinanzas({
      fecha_desde: appliedDesde || undefined,
      fecha_hasta: appliedHasta || undefined,
    }),
  });

  const aplicar = () => {
    if (!validRange(desde, hasta)) {
      setRangeError("fecha_desde debe ser <= fecha_hasta");
      return;
    }
    setRangeError(null);
    setAppliedDesde(desde);
    setAppliedHasta(hasta);
  };

  const limpiar = () => {
    setDesde("");
    setHasta("");
    setAppliedDesde("");
    setAppliedHasta("");
    setRangeError(null);
  };

  return (
    <div>
      <PageHeader
        title="Finanzas"
        description="Rentabilidad estimada por lote y resultado financiero del período."
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs text-[var(--bf-muted)]">Desde<input type="date" className="bf-input mt-1 !py-1.5 text-sm" value={desde} onChange={(e) => setDesde(e.target.value)} /></label>
            <label className="text-xs text-[var(--bf-muted)]">Hasta<input type="date" className="bf-input mt-1 !py-1.5 text-sm" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>
            <button className="bf-btn-primary" type="button" onClick={aplicar}>Consultar</button>
            <button className="bf-btn-secondary" type="button" onClick={limpiar}>Quitar fechas</button>
          </div>
        }
      />

      {rangeError ? <div className="mb-4"><ErrorAlert message={rangeError} /></div> : null}
      {query.isLoading ? <LoadingState label="Calculando rentabilidad…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}

      {query.data ? (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Ventas" value={formatCop(query.data.ventas)} />
            <KpiCard label="Costo de ventas" value={formatCop(query.data.costo_ventas_estimado)} hint="Costo estimado de la biomasa vendida" />
            <KpiCard label="Utilidad bruta" value={formatCop(query.data.utilidad_bruta)} hint={query.data.margen_bruto_pct == null ? "Margen N/D" : `${formatNumber(query.data.margen_bruto_pct, { maximumFractionDigits: 2 })} % margen bruto`} emphasize={Number(query.data.utilidad_bruta) < 0} />
            <KpiCard label="Utilidad neta" value={formatCop(query.data.utilidad_neta)} hint={query.data.margen_neto_pct == null ? "Margen N/D" : `${formatNumber(query.data.margen_neto_pct, { maximumFractionDigits: 2 })} % margen neto`} emphasize={Number(query.data.utilidad_neta) < 0} />
          </section>

          <section className="mt-8 grid gap-3 sm:grid-cols-3">
            <KpiCard label="Gastos operativos" value={formatCop(query.data.gastos_operativos)} />
            <KpiCard label="Kg vendidos" value={formatNumber(query.data.kg_vendidos, { maximumFractionDigits: 3 })} hint="Biomasa comercializada" />
            <KpiCard label="Costo promedio/kg" value={formatCop(query.data.costo_promedio_kg_vendido)} hint={`${formatNumber(query.data.lotes_con_ventas)} lote(s) con ventas`} />
          </section>

          <section className="mt-8">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-lg font-semibold">Rentabilidad por lote</h2>
                <p className="text-sm text-[var(--bf-muted)]">Costo de producción, costo de ventas y margen de cada lote con ventas.</p>
              </div>
              <Link to="/finanzas/ventas" className="bf-btn-secondary">Ver ventas</Link>
            </div>
            <div className="overflow-x-auto rounded-xl border border-[var(--bf-border)] bg-white">
              <table className="min-w-full text-sm">
                <thead className="border-b border-[var(--bf-border)] bg-[var(--bf-chip)]">
                  <tr>
                    {['Lote','Ventas','Kg vendidos','Costo producción','Costo/kg','Costo ventas','Utilidad','Margen'].map((h) => <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {query.data.lotes.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-[var(--bf-muted)]">No hay ventas para el período seleccionado.</td></tr>
                  ) : query.data.lotes.map((lote) => (
                    <tr key={lote.lote_id} className="border-b border-[var(--bf-border)] last:border-0">
                      <td className="px-4 py-3 font-medium">{lote.codigo}</td>
                      <td className="px-4 py-3">{formatCop(lote.ventas)}</td>
                      <td className="px-4 py-3">{formatNumber(lote.kg_vendidos, { maximumFractionDigits: 3 })}</td>
                      <td className="px-4 py-3">{formatCop(lote.costo_produccion)}</td>
                      <td className="px-4 py-3">{formatCop(lote.costo_por_kg)}</td>
                      <td className="px-4 py-3">{formatCop(lote.costo_ventas_estimado)}</td>
                      <td className={`px-4 py-3 font-semibold ${Number(lote.utilidad_bruta) < 0 ? "text-amber-800" : ""}`}>{formatCop(lote.utilidad_bruta)}</td>
                      <td className="px-4 py-3">{lote.margen_bruto_pct == null ? "N/D" : `${formatNumber(lote.margen_bruto_pct, { maximumFractionDigits: 2 })} %`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 rounded-xl border border-[var(--bf-border)] bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Metodología</p>
            <p className="mt-2 text-sm text-[var(--bf-muted)]">{query.data.metodologia}</p>
          </section>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Link to="/finanzas/gastos" className="rounded-xl border border-[var(--bf-border)] bg-white p-5 hover:border-[var(--bf-accent)]">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Gastos</p>
              <p className="mt-2 font-display text-xl font-semibold">Registrar y consultar gastos</p>
            </Link>
            <Link to="/finanzas/ventas" className="rounded-xl border border-[var(--bf-border)] bg-white p-5 hover:border-[var(--bf-accent)]">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Ventas</p>
              <p className="mt-2 font-display text-xl font-semibold">Registrar y consultar ventas</p>
            </Link>
          </div>
        </>
      ) : null}
    </div>
  );
}
