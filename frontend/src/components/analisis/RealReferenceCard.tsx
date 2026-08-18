import { StatusBadge } from "../StatusBadge";
import { formatDate, formatNumber } from "../../utils/format";
import type { EvaluacionIndicador } from "../../types/analisis";

type RealReferenceCardProps = {
  evaluacion: EvaluacionIndicador;
};

function numero(valor: string | number, digitos = 4): string {
  return formatNumber(valor, { maximumFractionDigits: digitos });
}

function badge(evaluacion: EvaluacionIndicador) {
  if (evaluacion.cumplimiento_rango === "DENTRO_RANGO") {
    return <StatusBadge label="Dentro del rango" tone="ok" />;
  }
  if (evaluacion.cumplimiento_rango === "FUERA_RANGO") {
    return <StatusBadge label="Fuera del rango" tone="danger" />;
  }
  switch (evaluacion.estado_analitico) {
    case "NORMAL":
      return <StatusBadge label="🟢 NORMAL" tone="ok" />;
    case "ALERTA":
      return <StatusBadge label="🟡 ALERTA" tone="warn" />;
    case "CRITICO":
      return <StatusBadge label="🔴 CRÍTICO" tone="danger" />;
    case "SIN_DATOS":
      return <StatusBadge label="⚪ SIN DATOS" tone="neutral" />;
    case "SIN_REFERENCIA":
      return <StatusBadge label="⚫ SIN REFERENCIA" tone="neutral" />;
    default:
      return null;
  }
}

/**
 * Presenta exactamente la evaluación entregada por el backend. No deriva
 * objetivos, rangos, desviaciones ni estados.
 */
export function RealReferenceCard({ evaluacion }: RealReferenceCardProps) {
  const unidad = evaluacion.unidad ? ` ${evaluacion.unidad}` : "";
  const rango =
    evaluacion.minimo !== null || evaluacion.maximo !== null
      ? `${evaluacion.minimo === null ? "N/D" : numero(evaluacion.minimo)} – ${
          evaluacion.maximo === null ? "N/D" : numero(evaluacion.maximo)
        }${unidad}`
      : null;

  return (
    <article className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-display text-sm font-semibold text-[var(--bf-ink)]">
          {evaluacion.etiqueta}
        </h3>
        {badge(evaluacion)}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <Dato
          label="Real"
          valor={
            evaluacion.real === null ? "N/D" : `${numero(evaluacion.real)}${unidad}`
          }
        />
        {evaluacion.objetivo !== null ? (
          <Dato label="Objetivo" valor={`${numero(evaluacion.objetivo)}${unidad}`} />
        ) : null}
        {rango ? <Dato label="Rango" valor={rango} /> : null}
        {evaluacion.diferencia_objetivo !== null ? (
          <Dato
            label="Diferencia"
            valor={`${numero(evaluacion.diferencia_objetivo)}${unidad}`}
          />
        ) : null}
        {evaluacion.diferencia_objetivo_porcentaje !== null ? (
          <Dato
            label="Desviación"
            valor={`${numero(evaluacion.diferencia_objetivo_porcentaje, 2)} %`}
          />
        ) : null}
        {evaluacion.desviacion_rango !== null ? (
          <Dato
            label="Desviación del límite"
            valor={`${numero(evaluacion.desviacion_rango)}${unidad}`}
          />
        ) : null}
      </dl>

      <p className="mt-3 text-xs text-[var(--bf-muted)]">{evaluacion.explicacion}</p>
      {evaluacion.referencia ? (
        <p className="mt-2 text-xs text-[var(--bf-muted)]">
          <span className="font-medium text-[var(--bf-ink)]">Referencia:</span>{" "}
          {evaluacion.referencia}
        </p>
      ) : null}
      {evaluacion.fecha_real || evaluacion.fecha_referencia ? (
        <p className="mt-1 text-xs text-[var(--bf-muted)]">
          {evaluacion.fecha_real ? `Dato: ${formatDate(evaluacion.fecha_real)}` : ""}
          {evaluacion.fecha_real && evaluacion.fecha_referencia ? " · " : ""}
          {evaluacion.fecha_referencia
            ? `Referencia: ${formatDate(evaluacion.fecha_referencia)}`
            : ""}
        </p>
      ) : null}
    </article>
  );
}

function Dato({ label, valor }: { label: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{label}</dt>
      <dd className="mt-0.5 font-medium text-[var(--bf-ink)]">{valor}</dd>
    </div>
  );
}
