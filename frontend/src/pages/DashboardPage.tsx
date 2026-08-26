import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchDashboardProduccion, fetchDashboardResumen } from "../api/dashboard";
import { getComparativoEstanques } from "../api/analisis";
import { ComparativoEstanquesPanel } from "./produccion/ComparativoEstanquesPanel";
import { ErrorAlert } from "../components/ErrorAlert";
import { EmptyState } from "../components/EmptyState";
import { KpiCard } from "../components/KpiCard";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { FCA_GRANJA_ND } from "../utils/fcaPresentacion";
import { apiErrorMessage } from "../utils/apiError";
import { formatChartValue, formatCop, formatDate, formatNumber } from "../utils/format";
import type { DashboardResumen } from "../types/dashboard";

function moneyNumber(value: string | number): number {
  const amount = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(amount) ? amount : 0;
}

function rangeIsValid(desde: string, hasta: string): boolean {
  if (!desde || !hasta) {
    return true;
  }
  return desde <= hasta;
}

function periodoLabel(data: DashboardResumen, appliedDesde: string, appliedHasta: string): string {
  const desde = data.periodo.fecha_desde ?? (appliedDesde || null);
  const hasta = data.periodo.fecha_hasta ?? (appliedHasta || null);
  if (!desde && !hasta) {
    return "Sin filtro de fechas: el backend incluye todo el histórico en ventas, compras, gastos, mantenimientos y energía. Stock, lotes, equipos y alarmas son un snapshot actual.";
  }
  const a = desde ? formatDate(desde) : "inicio";
  const b = hasta ? formatDate(hasta) : "hoy";
  return `Período consultado: ${a} — ${b}. Stock, lotes activos, equipos y alarmas pendientes no dependen del período.`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
        {title}
      </h2>
      {children}
    </section>
  );
}

function SkeletonKpis() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          key={index}
          className="h-[104px] animate-pulse rounded-2xl border border-[var(--bf-border)] bg-white"
        />
      ))}
    </div>
  );
}

export function DashboardPage() {
  const [desdeDraft, setDesdeDraft] = useState("");
  const [hastaDraft, setHastaDraft] = useState("");
  const [appliedDesde, setAppliedDesde] = useState("");
  const [appliedHasta, setAppliedHasta] = useState("");
  const [rangeError, setRangeError] = useState<string | null>(null);

  const validDraft = rangeIsValid(desdeDraft, hastaDraft);

  const query = useQuery({
    queryKey: ["dashboard", "resumen", appliedDesde, appliedHasta],
    queryFn: () =>
      fetchDashboardResumen({
        fecha_desde: appliedDesde || undefined,
        fecha_hasta: appliedHasta || undefined,
      }),
  });
  const analisisQuery = useQuery({
    queryKey: ["analisis-estanques", true],
    queryFn: () => getComparativoEstanques(true),
  });
  const produccionQuery = useQuery({
    queryKey: ["dashboard", "produccion", appliedDesde, appliedHasta],
    queryFn: () =>
      fetchDashboardProduccion({
        fecha_desde: appliedDesde || undefined,
        fecha_hasta: appliedHasta || undefined,
      }),
  });

  const inventarioChart = useMemo(() => {
    if (!query.data) return [];
    return [
      { nombre: "Activos", valor: query.data.productos_activos },
      { nombre: "Sin stock", valor: query.data.productos_sin_stock },
      { nombre: "Stock bajo", valor: query.data.productos_stock_bajo },
    ];
  }, [query.data]);

  const finanzasChart = useMemo(() => {
    if (!query.data) return [];
    return [
      { nombre: "Ventas", valor: moneyNumber(query.data.ventas.total) },
      { nombre: "Compras", valor: moneyNumber(query.data.compras.total) },
      { nombre: "Gastos", valor: moneyNumber(query.data.gastos.total) },
    ];
  }, [query.data]);

  function aplicarFiltro() {
    if (!rangeIsValid(desdeDraft, hastaDraft)) {
      setRangeError("fecha_desde debe ser <= fecha_hasta");
      return;
    }
    setRangeError(null);
    setAppliedDesde(desdeDraft);
    setAppliedHasta(hastaDraft);
  }

  function limpiarFiltro() {
    setDesdeDraft("");
    setHastaDraft("");
    setAppliedDesde("");
    setAppliedHasta("");
    setRangeError(null);
  }

  const data = query.data;
  const periodEmpty =
    Boolean(data) &&
    Boolean(appliedDesde || appliedHasta) &&
    data!.ventas.n === 0 &&
    data!.compras.n === 0 &&
    data!.gastos.n === 0 &&
    data!.mantenimientos_periodo === 0 &&
    data!.eventos_energia_periodo === 0;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Resumen de operación piscícola"
        actions={
          <form
            className="flex flex-wrap items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              aplicarFiltro();
            }}
          >
            <label className="text-xs text-[var(--bf-muted)]">
              Desde
              <input
                type="date"
                className="bf-input mt-1 !py-1.5 text-sm"
                value={desdeDraft}
                onChange={(event) => setDesdeDraft(event.target.value)}
              />
            </label>
            <label className="text-xs text-[var(--bf-muted)]">
              Hasta
              <input
                type="date"
                className="bf-input mt-1 !py-1.5 text-sm"
                value={hastaDraft}
                onChange={(event) => setHastaDraft(event.target.value)}
              />
            </label>
            <button type="submit" className="bf-btn-primary" disabled={!validDraft}>
              Consultar
            </button>
            <button type="button" className="bf-btn-secondary" onClick={limpiarFiltro}>
              Quitar fechas
            </button>
          </form>
        }
      />

      {rangeError ? (
        <div className="mb-4">
          <ErrorAlert message={rangeError} />
        </div>
      ) : null}

      {query.isLoading ? (
        <div>
          <LoadingState label="Cargando resumen operativo…" />
          <SkeletonKpis />
        </div>
      ) : null}

      {query.isError ? (
        <div className="space-y-3">
          <ErrorAlert message={apiErrorMessage(query.error)} />
          <button type="button" className="bf-btn-primary" onClick={() => void query.refetch()}>
            Reintentar
          </button>
        </div>
      ) : null}

      {data ? (
        <>
          <p className="mb-4 text-sm text-[var(--bf-muted)]">{periodoLabel(data, appliedDesde, appliedHasta)}</p>

          <Section title="Producción">
            {analisisQuery.isLoading ? <LoadingState label="Cargando resumen piscícola…" /> : null}
            {analisisQuery.isError ? <ErrorAlert message={apiErrorMessage(analisisQuery.error)} /> : null}
            {analisisQuery.data && analisisQuery.data.resumen.estanques === 0 ? (
              <EmptyState
                title="Sin datos productivos"
                description="No hay estanques registrados. Los indicadores de población, biomasa y supervivencia aparecen cuando exista un ciclo activo. El FCA de granja permanece N/D mientras no exista regla de agregación."
              />
            ) : null}
            {analisisQuery.data && analisisQuery.data.resumen.estanques > 0 ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <KpiCard
                    label="Estanques activos"
                    value={`${formatNumber(analisisQuery.data.resumen.estanques_con_lote_activo)} / ${formatNumber(analisisQuery.data.resumen.estanques)}`}
                    to="/produccion/estanques"
                  />
                  <KpiCard
                    label="Lotes activos"
                    value={formatNumber(data.lotes_activos)}
                    to="/produccion/lotes"
                  />
                  <KpiCard
                    label="Población"
                    value={analisisQuery.data.resumen.estanques_con_lote_activo === 0 ? "N/D" : formatNumber(analisisQuery.data.resumen.poblacion_estimada)}
                  />
                  <KpiCard
                    label="Biomasa"
                    value={analisisQuery.data.resumen.biomasa_actual_kg == null ? "N/D" : formatNumber(analisisQuery.data.resumen.biomasa_actual_kg, { maximumFractionDigits: 3 })}
                    hint="kg"
                  />
                  <KpiCard label="Supervivencia" value={analisisQuery.data.resumen.supervivencia_porcentaje == null ? "N/D" : `${formatNumber(analisisQuery.data.resumen.supervivencia_porcentaje, { maximumFractionDigits: 2 })} %`} />
                  <KpiCard
                    label="Alimento"
                    value={analisisQuery.data.resumen.alimento_real_acumulado_kg == null ? "N/D" : formatNumber(analisisQuery.data.resumen.alimento_real_acumulado_kg, { maximumFractionDigits: 3 })}
                    hint="kg acumulados del ciclo activo"
                  />
                  <KpiCard
                    label="FCA de granja"
                    value="N/D"
                    hint={FCA_GRANJA_ND}
                    title={analisisQuery.data.resumen.fca_motivo}
                  />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link to="/produccion/estanques" className="bf-btn-primary inline-flex">
                    Ir a estanques
                  </Link>
                </div>
              </>
            ) : null}
          </Section>

          <Section title="Comparación de estanques">
            <p className="mb-3 text-sm text-[var(--bf-muted)]">
              Un renglón por estanque con el lote activo. Los indicadores los entrega el API; esta
              tabla no recalcula. El FCA acumulado es del lote activo, no del estanque. El FCA de
              granja no se agrega. Entre al estanque para el nivel 3: ficha, lote y gráficas.
            </p>
            <ComparativoEstanquesPanel soloActivos mostrarResumen={false} />
          </Section>

          <Section title="Estado de operación">
            {produccionQuery.isLoading ? <LoadingState label="Cargando producción del período…" /> : null}
            {produccionQuery.isError ? <ErrorAlert message={apiErrorMessage(produccionQuery.error)} /> : null}
            {produccionQuery.data ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <KpiCard label="Biomasa cosechada (kg)" value={formatNumber(produccionQuery.data.cosechas_peso_total_kg, { maximumFractionDigits: 3 })} hint={`${formatNumber(produccionQuery.data.cosechas_periodo)} cosecha(s)`} />
                <KpiCard label="Peces cosechados" value={formatNumber(produccionQuery.data.cosechas_peces)} />
                <KpiCard label="Mortalidad del período" value={formatNumber(produccionQuery.data.mortalidades_peces)} hint={`${formatNumber(produccionQuery.data.mortalidades_periodo)} registro(s)`} />
                <KpiCard label="Registros de alimentación" value={formatNumber(produccionQuery.data.alimentaciones_periodo)} hint="Conteo; no mezcla unidades." />
                <KpiCard label="Mediciones de agua" value={formatNumber(produccionQuery.data.mediciones_agua_periodo)} hint={`${formatNumber(produccionQuery.data.mediciones_agua_fuera_rango)} fuera de rango con referencia.`} />
              </div>
            ) : null}
          </Section>

          <Section title="Operación ahora">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                label="Lotes activos"
                value={formatNumber(data.lotes_activos)}
                hint="Snapshot · estado ACTIVO"
                to="/produccion/lotes"
              />
              <KpiCard
                label="Alarmas pendientes"
                value={formatNumber(data.alarmas_pendientes)}
                hint="Sistema general de alarmas"
                to="/alarmas"
                emphasize={data.alarmas_pendientes > 0}
              />
              <KpiCard
                label="Stock bajo"
                value={formatNumber(data.productos_stock_bajo)}
                hint="Productos activos bajo mínimo"
                to="/inventario"
                emphasize={data.productos_stock_bajo > 0}
              />
              <KpiCard
                label="Equipos operativos"
                value={formatNumber(data.equipos_operativos)}
                hint={`${formatNumber(data.equipos_activos)} equipos activos`}
                to="/equipos"
              />
            </div>
          </Section>

          <Section title="Inventario">
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard
                  label="Productos activos"
                  value={formatNumber(data.productos_activos)}
                  to="/inventario"
                />
                <KpiCard
                  label="Sin stock"
                  value={formatNumber(data.productos_sin_stock)}
                  to="/inventario"
                  emphasize={data.productos_sin_stock > 0}
                />
                <KpiCard
                  label="Stock bajo"
                  value={formatNumber(data.productos_stock_bajo)}
                  to="/inventario"
                />
              </div>
              <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
                <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--bf-muted)]">
                  Conteo de productos (no suma cantidades)
                </p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={inventarioChart} barCategoryGap="28%">
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--bf-border)" vertical={false} />
                      <XAxis dataKey="nombre" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                      <Tooltip
                        formatter={(value) => formatChartValue(value)}
                      />
                      <Bar dataKey="valor" fill="var(--bf-accent)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </Section>

          <Section title="Equipos y energía">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard label="Equipos activos" value={formatNumber(data.equipos_activos)} to="/equipos" />
              <KpiCard label="Equipos operativos" value={formatNumber(data.equipos_operativos)} to="/equipos" />
              <KpiCard
                label="Mantenimientos"
                value={formatNumber(data.mantenimientos_periodo)}
                hint="En el período consultado"
                to="/equipos/mantenimientos"
              />
              <KpiCard
                label="Eventos de energía"
                value={formatNumber(data.eventos_energia_periodo)}
                hint="En el período consultado"
                to="/energia"
              />
            </div>
          </Section>

          <Section title="Movimiento económico">
            {periodEmpty ? (
              <p className="mb-3 text-sm text-[var(--bf-muted)]">
                No hay datos disponibles para el período seleccionado.
              </p>
            ) : null}
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard
                  label="Ventas"
                  value={formatCop(data.ventas.total)}
                  hint={`${formatNumber(data.ventas.n)} registro(s)`}
                  to="/finanzas"
                />
                <KpiCard
                  label="Compras"
                  value={formatCop(data.compras.total)}
                  hint={`${formatNumber(data.compras.n)} registro(s)`}
                  to="/compras"
                />
                <KpiCard
                  label="Gastos"
                  value={formatCop(data.gastos.total)}
                  hint={`${formatNumber(data.gastos.n)} registro(s)`}
                  to="/finanzas"
                />
              </div>
              <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
                <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--bf-muted)]">
                  Totales del período (COP)
                </p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={finanzasChart} barCategoryGap="28%">
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--bf-border)" vertical={false} />
                      <XAxis dataKey="nombre" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => formatCop(value)} width={88} />
                      <Tooltip
                        formatter={(value) =>
                          value === null || value === undefined
                            ? "N/D"
                            : formatCop(typeof value === "number" ? value : Number(value))
                        }
                      />
                      <Bar dataKey="valor" fill="#1c4f43" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </Section>

          <Section title="Alarmas">
            <div className="flex flex-col gap-3 rounded-xl border border-[var(--bf-border)] bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-[var(--bf-muted)]">
                  Pendientes
                </p>
                <p className="mt-1 font-display text-2xl font-semibold text-[var(--bf-ink)]">
                  {formatNumber(data.alarmas_pendientes)}
                </p>
                <p className="mt-1 text-sm text-[var(--bf-muted)]">
                  El resumen no entrega atendidas ni cerradas. Stock bajo está en Inventario, no aquí.
                </p>
              </div>
              <Link to="/alarmas" className="bf-btn-primary shrink-0 justify-center">
                Ver alarmas
              </Link>
            </div>
          </Section>
        </>
      ) : null}

      {query.isFetching && !query.isLoading ? (
        <p className="mt-4 text-xs text-[var(--bf-muted)]">Actualizando…</p>
      ) : null}
    </div>
  );
}
