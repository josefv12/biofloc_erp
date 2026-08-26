import type { LineaReferencia, SerieDefinicion } from "../components/charts/TimeSeriesChart";
import { COLORES_COMPARATIVA } from "./comparativeColors";
import type { CumplimientoRango, EvaluacionIndicador, EstadoAnalitico } from "../types/analisis";
import { formatNumber } from "./format";
import { toNumber } from "./series";

export type StatusTone = "neutral" | "ok" | "warn" | "danger";

export function toneCumplimiento(cumplimiento: CumplimientoRango): StatusTone {
  switch (cumplimiento) {
    case "DENTRO_RANGO":
      return "ok";
    case "FUERA_RANGO":
      return "danger";
    default:
      return "neutral";
  }
}

export function toneEstadoAnalitico(estado: EstadoAnalitico | null | undefined): StatusTone {
  switch (estado) {
    case "NORMAL":
      return "ok";
    case "ALERTA":
      return "warn";
    case "CRITICO":
      return "danger";
    default:
      return "neutral";
  }
}

export function cumplimientoPorRango(
  real: number | null,
  minimo: number | null,
  maximo: number | null,
): CumplimientoRango {
  if (real == null || !Number.isFinite(real)) return "NO_EVALUABLE";
  if (minimo == null && maximo == null) return "NO_EVALUABLE";
  if (minimo != null && real < minimo) return "FUERA_RANGO";
  if (maximo != null && real > maximo) return "FUERA_RANGO";
  return "DENTRO_RANGO";
}

export function etiquetaCumplimiento(cumplimiento: CumplimientoRango): string {
  switch (cumplimiento) {
    case "DENTRO_RANGO":
      return "DENTRO DE RANGO";
    case "FUERA_RANGO":
      return "FUERA DE RANGO";
    default:
      return cumplimiento;
  }
}

export function buscarEvaluacion(
  evaluaciones: EvaluacionIndicador[],
  indicador: string,
): EvaluacionIndicador | undefined {
  return evaluaciones.find((item) => item.indicador === indicador);
}

/** Título legible para recomendaciones (usa etiqueta del backend, nunca `agua:1`). */
export function nombreIndicadorCalidad(
  indicador: string,
  evaluaciones: EvaluacionIndicador[],
  nombresAgua?: { parametro_id: number; parametro: string }[],
): string {
  const evaluacion = buscarEvaluacion(evaluaciones, indicador);
  if (evaluacion?.etiqueta) {
    if (indicador === "volumen_sedimentable" || evaluacion.etiqueta === "Volumen sedimentable") {
      return "Sólidos sedimentables";
    }
    if (indicador === "alimentacion_diaria_kg") return "Alimentación";
    if (evaluacion.etiqueta !== "Agua") return evaluacion.etiqueta;
  }

  const matchAgua = indicador.match(/^agua:(\d+)$/);
  if (matchAgua && nombresAgua?.length) {
    const paramId = Number(matchAgua[1]);
    const medicion = nombresAgua.find((row) => row.parametro_id === paramId);
    if (medicion?.parametro) return medicion.parametro;
  }
  if (/^agua:\d+$/i.test(indicador)) return "Parámetro de agua";
  if (indicador === "volumen_sedimentable") return "Sólidos sedimentables";
  return indicador.replace(/_/g, " ");
}

export function tituloRecomendacion(
  indicador: string,
  evaluaciones: EvaluacionIndicador[],
  nombresAgua?: { parametro_id: number; parametro: string }[],
): string {
  const nombre = nombreIndicadorCalidad(indicador, evaluaciones, nombresAgua);
  const evaluacion = buscarEvaluacion(evaluaciones, indicador);
  if (evaluacion?.cumplimiento_rango === "FUERA_RANGO") {
    return `${nombre} fuera de rango`;
  }
  return nombre;
}

export function referenciasDesdeEvaluacion(
  evaluacion: EvaluacionIndicador | undefined,
  digitos = 4,
): LineaReferencia[] {
  if (!evaluacion) return [];
  const refs: LineaReferencia[] = [];
  const min = toNumber(evaluacion.minimo);
  const obj = toNumber(evaluacion.objetivo);
  const max = toNumber(evaluacion.maximo);
  if (min !== null) {
    refs.push({
      valor: min,
      etiqueta: `Mín ${formatNumber(min, { maximumFractionDigits: digitos })}`,
      color: "#94a3b8",
    });
  }
  if (obj !== null) {
    refs.push({
      valor: obj,
      etiqueta: `Objetivo ${formatNumber(obj, { maximumFractionDigits: digitos })}`,
      color: "#64748b",
    });
  }
  if (max !== null) {
    refs.push({
      valor: max,
      etiqueta: `Máx ${formatNumber(max, { maximumFractionDigits: digitos })}`,
      color: "#94a3b8",
    });
  }
  return refs;
}

export function bordeEstado(tone: StatusTone): string {
  switch (tone) {
    case "ok":
      return "border-emerald-200";
    case "warn":
      return "border-amber-200";
    case "danger":
      return "border-red-200";
    default:
      return "border-[var(--bf-border)]";
  }
}

/** Color de línea para serie Real según cumplimiento del backend. */
export function colorSerieReal(cumplimiento: CumplimientoRango | undefined): string {
  switch (cumplimiento) {
    case "DENTRO_RANGO":
      return COLORES_COMPARATIVA.realOk;
    case "FUERA_RANGO":
      return COLORES_COMPARATIVA.realFuera;
    default:
      return COLORES_COMPARATIVA.realNeutral;
  }
}

/** Color de la serie Real usando cumplimiento y estado analítico (ALERTA → amarillo). */
export function colorSerieRealEvaluacion(evaluacion: EvaluacionIndicador | undefined): string {
  if (!evaluacion) return COLORES_COMPARATIVA.realNeutral;
  if (evaluacion.estado_analitico === "ALERTA") return COLORES_COMPARATIVA.realAlerta;
  if (evaluacion.estado_analitico === "CRITICO") return COLORES_COMPARATIVA.realFuera;
  return colorSerieReal(
    evaluacion.cumplimiento_rango === "NO_EVALUABLE" ? undefined : evaluacion.cumplimiento_rango,
  );
}

export type ReferenciaComparativa = {
  minimo: number | null;
  maximo: number | null;
  objetivo: number | null;
};

/** Extrae referencia comparativa desde evaluación del backend (sin inventar objetivo). */
export function referenciaDesdeEvaluacion(evaluacion: EvaluacionIndicador | undefined): ReferenciaComparativa {
  return {
    minimo: evaluacion ? toNumber(evaluacion.minimo) : null,
    maximo: evaluacion ? toNumber(evaluacion.maximo) : null,
    objetivo: evaluacion ? toNumber(evaluacion.objetivo) : null,
  };
}

/** Series Recharts para gráfica real vs referencia. */
export function seriesComparativas(
  ref: ReferenciaComparativa,
  colorReal: string,
): SerieDefinicion[] {
  const series: SerieDefinicion[] = [{ key: "real", nombre: "Real", color: colorReal }];
  if (ref.objetivo !== null) {
    series.push({ key: "objetivo", nombre: "Objetivo", color: COLORES_COMPARATIVA.objetivo, referencia: true });
  }
  if (ref.minimo !== null) {
    series.push({ key: "minimo", nombre: "Mínimo", color: COLORES_COMPARATIVA.minimo, referencia: true });
  }
  if (ref.maximo !== null) {
    series.push({ key: "maximo", nombre: "Máximo", color: COLORES_COMPARATIVA.maximo, referencia: true });
  }
  return series;
}

export function tieneReferenciaComparativa(ref: ReferenciaComparativa): boolean {
  return ref.minimo !== null || ref.maximo !== null || ref.objetivo !== null;
}
