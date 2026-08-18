import type { ReactNode } from "react";
import { formatNumber } from "../../utils/format";
import type { AnalisisStats } from "../../types/analisis";

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
  vacioMensaje = "Sin datos registrados para graficar.",
  children,
}: ChartCardProps) {
  const unidadMostrada = unidad ?? stats?.unidad ?? null;
  const numero = (valor: string | number | null) =>
    valor === null ? "—" : formatNumber(valor, { maximumFractionDigits: digitos });

  return (
    <section className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
          {title}
        </h3>
        {unidadMostrada ? (
          <span className="text-xs text-[var(--bf-muted)]">Unidad: {unidadMostrada}</span>
        ) : null}
      </div>
      {descripcion ? <p className="mt-1 text-xs text-[var(--bf-muted)]">{descripcion}</p> : null}

      {vacio ? (
        <p className="mt-4 rounded-lg border border-dashed border-[var(--bf-border)] px-4 py-6 text-center text-sm text-[var(--bf-muted)]">
          {vacioMensaje}
        </p>
      ) : (
        <div className="mt-3">{children}</div>
      )}

      {!vacio && stats && stats.n > 0 ? (
        <div className="mt-3 border-t border-[var(--bf-border)] pt-3 text-xs">
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
    <div>
      <p className="text-[var(--bf-muted)]">{label}</p>
      <p className="mt-0.5 font-medium text-[var(--bf-ink)]">
        {valor}
        {unidad && valor !== "—" ? ` ${unidad}` : ""}
      </p>
    </div>
  );
}
