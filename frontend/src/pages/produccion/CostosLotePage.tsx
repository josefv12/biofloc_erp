import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../components/PageHeader";
import { getCostosLote } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatNumber } from "../../utils/format";

export function CostosLotePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const loteId = Number(id);
  const query = useQuery({
    queryKey: ["costos-lote", loteId],
    queryFn: () => getCostosLote(loteId),
    enabled: Number.isInteger(loteId) && loteId > 0,
  });

  if (!Number.isInteger(loteId) || loteId <= 0) return <ErrorAlert message="Lote inválido." />;
  if (query.isLoading) return <LoadingState label="Calculando costos del lote…" />;
  if (query.isError) return <ErrorAlert message={apiErrorMessage(query.error)} />;
  if (!query.data) return null;
  const c = query.data;

  return (
    <div className="space-y-5">
      <PageHeader
        title={`Costos del lote ${c.codigo}`}
        description="Costos acumulados según consumo y registros realmente imputados al lote."
        actions={<button className="bf-btn-secondary" type="button" onClick={() => navigate(`/produccion/lotes/${c.lote_id}`)}>Volver al lote</button>}
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Costo de alevinos" value={formatCop(c.alevinos)} hint="Costo directo del lote." />
        <KpiCard label="Alimento consumido" value={formatCop(c.alimento)} hint={`${formatNumber(c.kg_alimento_suministrado, { maximumFractionDigits: 3 })} kg suministrados.`} />
        <KpiCard label="Otros costos directos" value={formatCop(c.otros_costos_directos)} />
        <KpiCard label="Costo directo del lote" value={formatCop(c.costo_directo_lote)} />
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Kg cosechados" value={formatNumber(c.kg_cosechados, { maximumFractionDigits: 3 })} />
        <KpiCard label="Costo por kg" value={c.costo_por_kg == null ? "N/D" : formatCop(c.costo_por_kg)} hint={c.costo_por_kg == null ? "Se calcula cuando exista cosecha." : "Costo directo acumulado / kg cosechados."} />
        <KpiCard label="Ventas" value={formatCop(c.ventas)} hint={`${formatNumber(c.kg_vendidos, { maximumFractionDigits: 3 })} kg vendidos.`} />
        <KpiCard label="Costo de ventas estimado" value={formatCop(c.costo_ventas_estimado)} />
      </section>

      <section className="rounded-2xl border border-[var(--bf-border)] bg-white p-4">
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Rentabilidad</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <KpiCard label="Utilidad bruta estimada" value={c.utilidad_bruta_estimada == null ? "N/D" : formatCop(c.utilidad_bruta_estimada)} hint="Ventas − costo de ventas estimado." />
          <KpiCard label="Margen bruto estimado" value={c.margen_bruto_estimado_pct == null ? "N/D" : `${formatNumber(c.margen_bruto_estimado_pct, { maximumFractionDigits: 2 })} %`} />
        </div>
      </section>

      {Number(c.costos_estanque_no_asignados) > 0 ? (
        <section className="rounded-2xl border border-[var(--bf-border)] bg-white p-4">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Costos del estanque pendientes de asignación</h2>
          <p className="mt-2 text-sm text-[var(--bf-muted)]">
            {formatCop(c.costos_estanque_no_asignados)} registrados en el estanque. No se cargan al lote automáticamente para evitar repartir un costo compartido de forma arbitraria.
          </p>
        </section>
      ) : null}

      <section className="rounded-2xl border border-[var(--bf-border)] bg-[var(--bf-surface-muted)] p-4 text-sm text-[var(--bf-muted)]">
        <strong className="text-[var(--bf-ink)]">Regla de costeo:</strong> una compra entra al inventario; solamente el alimento efectivamente suministrado al lote se convierte en costo del lote. Los alevinos y demás costos directos se imputan mediante registros de gasto del lote. Los costos del estanque permanecen separados hasta definir su prorrateo.
      </section>
    </div>
  );
}
