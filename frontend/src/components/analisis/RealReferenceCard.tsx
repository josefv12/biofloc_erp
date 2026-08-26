import { StatusBadge } from "../StatusBadge";
import { formatDate, formatNumber } from "../../utils/format";
import {
  bordeEstado,
  etiquetaCumplimiento,
  toneCumplimiento,
  toneEstadoAnalitico,
} from "../../utils/analisisStatus";
import type { EvaluacionIndicador } from "../../types/analisis";

type RealReferenceCardProps = {
  evaluacion: EvaluacionIndicador;
};

function numero(valor: string | number, digitos = 4): string {
  return formatNumber(valor, { maximumFractionDigits: digitos });
}

function tituloVisible(evaluacion: EvaluacionIndicador): string {
  if (evaluacion.indicador === "volumen_sedimentable" || evaluacion.etiqueta === "Volumen sedimentable") {
    return "Sólidos sedimentables";
  }
  if (/^agua:\d+$/i.test(evaluacion.indicador) && (!evaluacion.etiqueta || evaluacion.etiqueta === "Agua")) {
    return "Parámetro de agua";
  }
  return evaluacion.etiqueta;
}

function badge(evaluacion: EvaluacionIndicador) {
  const cumplimientoTone = toneCumplimiento(evaluacion.cumplimiento_rango);
  const cumplimiento =
    evaluacion.cumplimiento_rango === "NO_EVALUABLE" ? null : (
      <StatusBadge label={etiquetaCumplimiento(evaluacion.cumplimiento_rango)} tone={cumplimientoTone} />
    );
  let estado = null;
  switch (evaluacion.estado_analitico) {
    case "NORMAL":
      estado = <StatusBadge label="NORMAL" tone="ok" />;
      break;
    case "ALERTA":
      estado = <StatusBadge label="ALERTA" tone="warn" />;
      break;
    case "CRITICO":
      estado = <StatusBadge label="CRÍTICO" tone="danger" />;
      break;
    case "SIN_DATOS":
      estado = <StatusBadge label="N/D — Sin medición" tone="neutral" />;
      break;
    case "SIN_REFERENCIA":
      estado = <StatusBadge label="N/D — Sin referencia configurada" tone="neutral" />;
      break;
    default:
      estado = null;
  }
  return (
    <span className="flex flex-wrap gap-1">
      {cumplimiento}
      {estado}
    </span>
  );
}

/**
 * Presenta exactamente la evaluación entregada por el backend. No deriva
 * objetivos, rangos, desviaciones ni estados. El objetivo no sustituye el rango.
 */
export function RealReferenceCard({ evaluacion }: RealReferenceCardProps) {
  const unidad = evaluacion.unidad ? ` ${evaluacion.unidad}` : "";
  const borde =
    evaluacion.cumplimiento_rango === "NO_EVALUABLE"
      ? bordeEstado(toneEstadoAnalitico(evaluacion.estado_analitico))
      : bordeEstado(toneCumplimiento(evaluacion.cumplimiento_rango));
  const realTxt =
    evaluacion.real === null
      ? "N/D — Sin medición"
      : `${numero(evaluacion.real)}${unidad}`;
  const hayRango = evaluacion.minimo !== null || evaluacion.maximo !== null;
  const rangoTxt = hayRango
    ? `${evaluacion.minimo == null ? "—" : numero(evaluacion.minimo)} – ${
        evaluacion.maximo == null ? "—" : numero(evaluacion.maximo)
      }${unidad}`
    : "N/D — Sin referencia configurada";

  return (
    <article className={`rounded-2xl border bg-white p-4 shadow-[0_1px_2px_rgba(16,40,33,0.04)] ${borde}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-display text-sm font-semibold text-[var(--bf-ink)]">{tituloVisible(evaluacion)}</h3>
        {badge(evaluacion)}
      </div>

      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <Dato label="Valor real" valor={realTxt} />
        <Dato label="Rango" valor={rangoTxt} />
        {evaluacion.objetivo !== null ? (
          <Dato label="Objetivo" valor={`${numero(evaluacion.objetivo)}${unidad}`} />
        ) : null}
        {evaluacion.diferencia_objetivo !== null ? (
          <Dato label="Diferencia" valor={`${numero(evaluacion.diferencia_objetivo)}${unidad}`} />
        ) : null}
        {evaluacion.diferencia_objetivo_porcentaje !== null ? (
          <Dato label="Desviación" valor={`${numero(evaluacion.diferencia_objetivo_porcentaje, 2)} %`} />
        ) : null}
        {evaluacion.desviacion_rango !== null && evaluacion.cumplimiento_rango === "FUERA_RANGO" ? (
          <Dato label="Desviación del límite" valor={`${numero(evaluacion.desviacion_rango)}${unidad}`} />
        ) : null}
      </dl>

      <p className="mt-3 text-xs text-[var(--bf-muted)]">{evaluacion.explicacion}</p>
      {evaluacion.referencia ? (
        <p className="mt-2 text-xs text-[var(--bf-muted)]">
          <span className="font-medium text-[var(--bf-ink)]">Referencia:</span> {evaluacion.referencia}
        </p>
      ) : null}
      {evaluacion.fecha_real || evaluacion.fecha_referencia ? (
        <p className="mt-1 text-xs text-[var(--bf-muted)]">
          {evaluacion.fecha_real ? `Dato: ${formatDate(evaluacion.fecha_real)}` : ""}
          {evaluacion.fecha_real && evaluacion.fecha_referencia ? " · " : ""}
          {evaluacion.fecha_referencia ? `Referencia: ${formatDate(evaluacion.fecha_referencia)}` : ""}
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
