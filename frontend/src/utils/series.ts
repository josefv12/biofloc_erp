/**
 * Transformaciones de presentación para las series del núcleo analítico.
 *
 * Aquí no se calcula ningún indicador de negocio ni estadística: el backend
 * entrega los valores y sus descriptivos. Esto solo convierte decimales a
 * números seguros para graficar, agrupa por parámetro o unidad y totaliza por
 * día lo que ya viene convertido a kg.
 */
import { formatDateTime } from "./format";
import type {
  AnalisisAguaMedicion,
  AnalisisAlimentoRegistro,
  AnalisisBioflocMedicion,
  ApiDecimal,
} from "../types/analisis";

/** Convierte un decimal del API a número, o null si no es un número finito. */
export function toNumber(value: ApiDecimal | null | undefined): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(parsed) ? parsed : null;
}

export type PuntoSerie = {
  etiqueta: string;
  [serie: string]: string | number | null;
};

export type SerieAguaAgrupada = {
  parametro_id: number;
  parametro: string;
  unidad: string;
  valorMinimo: number | null;
  valorMaximo: number | null;
  puntos: PuntoSerie[];
};

/** Agrupa la serie de agua por parámetro, conservando el rango que envía el API. */
export function agruparAguaPorParametro(serie: AnalisisAguaMedicion[]): SerieAguaAgrupada[] {
  const grupos = new Map<number, SerieAguaAgrupada>();
  for (const medicion of serie) {
    let grupo = grupos.get(medicion.parametro_id);
    if (!grupo) {
      grupo = {
        parametro_id: medicion.parametro_id,
        parametro: medicion.parametro,
        unidad: medicion.unidad,
        valorMinimo: toNumber(medicion.valor_minimo),
        valorMaximo: toNumber(medicion.valor_maximo),
        puntos: [],
      };
      grupos.set(medicion.parametro_id, grupo);
    }
    grupo.puntos.push({ etiqueta: formatDateTime(medicion.fecha_hora), valor: toNumber(medicion.valor) });
  }
  return [...grupos.values()];
}

export type SerieBiofloc = {
  puntosVolumen: PuntoSerie[];
  puntosCn: PuntoSerie[];
};

/** Separa la serie de biofloc en volumen sedimentable y relación C:N. */
export function prepararBiofloc(serie: AnalisisBioflocMedicion[]): SerieBiofloc {
  const puntosVolumen: PuntoSerie[] = [];
  const puntosCn: PuntoSerie[] = [];
  for (const medicion of serie) {
    const etiqueta = formatDateTime(medicion.fecha_hora);
    puntosVolumen.push({ etiqueta, valor: toNumber(medicion.volumen_sedimentable) });
    const cn = toNumber(medicion.relacion_cn);
    if (cn !== null) {
      puntosCn.push({ etiqueta, valor: cn });
    }
  }
  return { puntosVolumen, puntosCn };
}

export type AlimentoDia = {
  fecha: string;
  etiqueta: string;
  cantidad: number;
};

/**
 * Totaliza por día el alimento que el backend ya convirtió a kg. Los registros
 * en unidades no convertibles se ignoran: nunca se asume una equivalencia.
 */
export function totalizarAlimentoKgPorDia(registros: AnalisisAlimentoRegistro[]): AlimentoDia[] {
  const porDia = new Map<string, number>();
  for (const registro of registros) {
    const cantidad = toNumber(registro.cantidad_kg);
    if (cantidad === null) {
      continue;
    }
    const fecha = registro.fecha_hora.slice(0, 10);
    porDia.set(fecha, (porDia.get(fecha) ?? 0) + cantidad);
  }
  return [...porDia.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fecha, cantidad]) => ({
      fecha,
      etiqueta: new Intl.DateTimeFormat("es-CO", {
        timeZone: "America/Bogota",
        day: "2-digit",
        month: "short",
      }).format(new Date(`${fecha}T12:00:00-05:00`)),
      cantidad,
    }));
}
