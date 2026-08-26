import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";

export function FinanzasPage() {
  return (
    <div>
      <PageHeader
        title="Finanzas"
        description="Movimientos económicos básicos de la granja. Totales del API. Sin utilidad, margen ni FCA."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/finanzas/gastos"
          className="rounded-xl border border-[var(--bf-border)] bg-white p-5 transition-colors hover:border-[var(--bf-accent)]"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Gastos</p>
          <p className="mt-2 font-display text-xl font-semibold">Registrar y consultar gastos</p>
          <p className="mt-1 text-sm text-[var(--bf-muted)]">Por categoría real del catálogo. Lote opcional.</p>
        </Link>
        <Link
          to="/finanzas/ventas"
          className="rounded-xl border border-[var(--bf-border)] bg-white p-5 transition-colors hover:border-[var(--bf-accent)]"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Ventas</p>
          <p className="mt-2 font-display text-xl font-semibold">Registrar y consultar ventas</p>
          <p className="mt-1 text-sm text-[var(--bf-muted)]">Se relacionan con lotes, no con productos ni inventario.</p>
        </Link>
      </div>
    </div>
  );
}
