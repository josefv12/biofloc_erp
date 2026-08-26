/** Textos de presentación del FCA. No calcula el indicador. */

export const FCA_LABEL = "FCA acumulado";

export const FCA_UNIDAD = "kg alimento / kg biomasa neta";

export const FCA_DEFINICION =
  "FCA acumulado: kg de alimento real suministrado por cada kg de biomasa neta producida.";

export const FCA_HINT_ECONOMICO =
  "Este indicador corresponde al FCA económico del lote. El alimento suministrado permanece en el cálculo aunque se hayan presentado mortalidades; por ello, una mayor mortalidad puede aumentar el FCA.";

export const FCA_ESPERADO_ND = "FCA esperado: sin referencia oficial configurada.";

export const FCA_GRANJA_ND =
  "Actualmente no existe una regla oficial para agregar el FCA de varios lotes.";

export const FCA_SERIE_TITULO = "Evolución del FCA acumulado";

export const FCA_SERIE_DESCRIPCION =
  "Cada punto es el FCA acumulado hasta esa biometría. No es un FCA de intervalo ni por etapa.";

export function fcaPeriodoHint(fechaCierre: string | null | undefined): string {
  return fechaCierre
    ? "Desde la siembra hasta el cierre del lote."
    : "Desde la siembra hasta la fecha de análisis.";
}

export function fcaHintDisponible(fechaCierre: string | null | undefined): string {
  return `${FCA_UNIDAD}. ${fcaPeriodoHint(fechaCierre)}`;
}

export function fcaHintNoDisponible(motivo: string | null | undefined): string {
  return motivo?.trim() ? motivo : "N/D";
}
