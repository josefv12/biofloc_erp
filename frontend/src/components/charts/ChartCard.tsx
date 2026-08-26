import type { ReactNode } from "react";
import { formatNumber } from "../../utils/format";
import type { AnalisisStats } from "../../types/analisis";
import { EmptyState } from "../EmptyState";

type ChartCardProps = {
  title: string;
  unidad?: string | null;
  descripcion?: string;
  stats?: AnalisisStats | null;
  digitos?: number;
  vacio?: boolean;
  vacioMensaje?: string;
  children: ReactNode;
};

/**
 * Marco común de las gráficas analíticas. Las estadísticas descriptivas las
 * calcula el backend; aquí solo se formatean.
 */
export function ChartCard({
  title,
  unidad,
  descripcion,
  stats,
  digitos = 3,
  vacio = false,
  vacioMensaje = "Sin datos suficientes para graficar.",
  children,
}: ChartCardProps) {
  const unidadMostrada = unidad ?? stats?.unidad ?? null;
  const numero = (valor: string | number | null) =>
    valor === null ? "—" : formatNumber(valor, { maximumFractionDigits: digitos });

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--bf-border)] bg-[linear-gradient(180deg,#ffffff_0%,#f7fbf8_100%)] p-5 shadow-[0_1px_2px_rgba(16,40,33,0.04),0_10px_28px_rgba(16,40,33,0.06)] transition-shadow duration-200 hover:shadow-[0_12px_32px_rgba(16,40,33,0.09)] bf-enter">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-display text-[13px] font-bold uppercase tracking-[0.08em] text-[var(--bf-ink)]">
          {title}
        </h3>
        {unidadMostrada ? (
          <span className="rounded-full bg-[var(--bf-chip)] px-2.5 py-0.5 text-[11px] font-medium text-[var(--bf-muted)]">
            Unidad: {unidadMostrada}
          </span>
        ) : null}
      </div>
      {descripcion ? (
        <p className="mt-1.5 text-xs leading-relaxed text-[var(--bf-muted)]">{descripcion}</p>
      ) : null}

      {vacio ? (
        <p className="mt-4">
          <EmptyState title={vacioMensaje} description="Cuando existan mediciones, la gráfica se construye con los valores del API." />
        </p>
      ) : (
        <div className="mt-3">{children}</div>
      )}

      {!vacio && stats && stats.n > 0 ? (
        <div className="mt-4 border-t border-[var(--bf-border)]/80 pt-3 text-xs">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <Dato label="n" valor={formatNumber(stats.n)} />
            <Dato label="Último" valor={numero(stats.ultimo)} unidad={unidadMostrada} />
            <Dato label="Promedio" valor={numero(stats.promedio)} unidad={unidadMostrada} />
            <Dato label="Mediana" valor={numero(stats.mediana)} unidad={unidadMostrada} />
            <Dato label="Mínimo" valor={numero(stats.minimo)} unidad={unidadMostrada} />
            <Dato label="Máximo" valor={numero(stats.maximo)} unidad={unidadMostrada} />
          </div>
          {stats.variacion_porcentual !== null ? (
            <p className="mt-2 text-[var(--bf-muted)]">
              Variación del primer al último valor:{" "}
              <span className="font-medium text-[var(--bf-ink)]">
                {formatNumber(stats.variacion_porcentual, { maximumFractionDigits: 2 })} %
              </span>
              . Métrica descriptiva, sin interpretación.
            </p>
          ) : null}
          {stats.n === 1 ? (
            <p className="mt-2 text-[var(--bf-muted)]">
              Una sola medición: no permite analizar evolución.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function Dato({ label, valor, unidad }: { label: string; valor: string; unidad?: string | null }) {
  return (
    <div className="rounded-lg bg-white/70 px-2 py-1.5">
      <p className="text-[11px] text-[var(--bf-muted)]">{label}</p>
      <p className="mt-0.5 font-semibold tabular-nums text-[var(--bf-ink)]">
        {valor}
        {unidad && valor !== "—" ? ` ${unidad}` : ""}
      </p>
    </div>
  );
}
