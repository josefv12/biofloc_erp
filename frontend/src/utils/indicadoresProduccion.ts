import { toNumber } from "./series";
import type { ApiDecimal } from "../types/analisis";

export const PESO_OBJETIVO_COSECHA_G = 400;
export const SEMANAS_CICLO_REFERENCIA = 20;
export const DIAS_CICLO_REFERENCIA = SEMANAS_CICLO_REFERENCIA * 7;

export function num(value: ApiDecimal | null | undefined): number | null {
  return toNumber(value ?? null);
}

export function mortalidadDiariaPromedio(mortalidadAcumulada: number, dias: number): number | null {
  if (dias <= 0) return null;
  return mortalidadAcumulada / dias;
}

export function racionSobreBiomasaPct(racionKg: number | null, biomasaKg: number | null): number | null {
  if (racionKg == null || biomasaKg == null || biomasaKg <= 0) return null;
  return (racionKg / biomasaKg) * 100;
}

export type BadgePeso = {
  label: "Por encima del esperado" | "En línea" | "Por debajo del esperado";
  tone: "ok" | "warn" | "neutral";
};

export function badgePesoVsEsperado(diffPct: number | null): BadgePeso | null {
  if (diffPct == null || !Number.isFinite(diffPct)) return null;
  if (diffPct > 0) return { label: "Por encima del esperado", tone: "ok" };
  if (diffPct < 0) return { label: "Por debajo del esperado", tone: "warn" };
  return { label: "En línea", tone: "neutral" };
}

export type ProyeccionCosecha = {
  objetivoPesoG: number;
  fechaMaximaCiclo: Date | null;
  fechaCosechaEstimada: Date | null;
  usaPrediccionCrecimiento: boolean;
  diasRestantesCalendario: number | null;
  diasRestantesCrecimiento: number | null;
  pesoProyectadoG: number | null;
  biomasaProyectadaKg: number | null;
  nota: string;
};

function addDays(base: Date, days: number): Date {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d;
}

export function fechaMaximaCicloDesdeSiembra(fechaSiembra: string): Date | null {
  const siembra = new Date(`${fechaSiembra}T00:00:00`);
  if (Number.isNaN(siembra.getTime())) return null;
  return addDays(siembra, DIAS_CICLO_REFERENCIA);
}

export function fechaLocalISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function mensajeRestantesCosecha(restantes: number): string {
  if (restantes === 0) return "Esta cosecha dejará el lote sin peces.";
  return `Después de esta cosecha quedarán ${restantes} peces.`;
}

/**
 * El ciclo productivo de referencia es de 20 semanas (140 días) desde la siembra.
 * La proyección por crecimiento usa peso real + GPD con objetivo de 400 g.
 */
export function proyectarCosecha(params: {
  fechaSiembra: string;
  diasCultivo: number;
  pesoActualG: number | null;
  gananciaDiariaG: number | null;
  poblacion: number | null;
}): ProyeccionCosecha {
  const siembra = new Date(`${params.fechaSiembra}T00:00:00`);
  const siembraValida = !Number.isNaN(siembra.getTime());
  const fechaMaximaCiclo = siembraValida ? fechaMaximaCicloDesdeSiembra(params.fechaSiembra) : null;

  let diasRestantesCalendario: number | null = null;
  if (siembraValida && fechaMaximaCiclo) {
    const fechaActual = addDays(siembra, Math.max(0, params.diasCultivo));
    diasRestantesCalendario = Math.max(
      0,
      Math.ceil((fechaMaximaCiclo.getTime() - fechaActual.getTime()) / 86400000),
    );
  }

  let diasPorPeso: number | null = null;
  if (params.pesoActualG != null && params.pesoActualG >= PESO_OBJETIVO_COSECHA_G) {
    diasPorPeso = 0;
  } else if (
    params.pesoActualG != null &&
    params.gananciaDiariaG != null &&
    params.gananciaDiariaG > 0
  ) {
    diasPorPeso = Math.ceil((PESO_OBJETIVO_COSECHA_G - params.pesoActualG) / params.gananciaDiariaG);
  }

  const usaPrediccionCrecimiento = diasPorPeso != null;
  const diasRestantesCrecimiento =
    diasPorPeso == null || diasRestantesCalendario == null
      ? null
      : Math.min(diasRestantesCalendario, Math.max(0, diasPorPeso));

  const fechaCosechaEstimada =
    siembraValida && diasRestantesCrecimiento != null
      ? addDays(siembra, params.diasCultivo + diasRestantesCrecimiento)
      : null;

  let pesoProyectadoG: number | null = null;
  if (params.pesoActualG != null && params.gananciaDiariaG != null && params.gananciaDiariaG > 0) {
    const dias = diasRestantesCrecimiento ?? 0;
    pesoProyectadoG = Math.min(PESO_OBJETIVO_COSECHA_G, params.pesoActualG + params.gananciaDiariaG * dias);
  } else if (params.pesoActualG != null && params.pesoActualG >= PESO_OBJETIVO_COSECHA_G) {
    pesoProyectadoG = params.pesoActualG;
  }

  const biomasaProyectadaKg =
    pesoProyectadoG != null && params.poblacion != null
      ? (params.poblacion * pesoProyectadoG) / 1000
      : null;

  let nota: string;
  if (!usaPrediccionCrecimiento) {
    nota =
      `Estimación de calendario (${SEMANAS_CICLO_REFERENCIA} semanas). No es una predicción de crecimiento real.`;
  } else if (params.pesoActualG != null && params.pesoActualG >= PESO_OBJETIVO_COSECHA_G) {
    nota = `Objetivo comercial de ${PESO_OBJETIVO_COSECHA_G} g alcanzado.`;
  } else if (diasPorPeso != null && diasRestantesCalendario != null && diasPorPeso > diasRestantesCalendario) {
    nota =
      `La predicción por GPD supera el ciclo de ${SEMANAS_CICLO_REFERENCIA} semanas; se usa la fecha máxima de ciclo como referencia.`;
  } else {
    nota = `Predicción de crecimiento con peso real y GPD hacia ${PESO_OBJETIVO_COSECHA_G} g.`;
  }

  return {
    objetivoPesoG: PESO_OBJETIVO_COSECHA_G,
    fechaMaximaCiclo,
    fechaCosechaEstimada,
    usaPrediccionCrecimiento,
    diasRestantesCalendario,
    diasRestantesCrecimiento,
    pesoProyectadoG,
    biomasaProyectadaKg,
    nota,
  };
}
