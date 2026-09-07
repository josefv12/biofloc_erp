/**
 * Conversiones exclusivamente de presentación.
 *
 * unidad interna = cómo se almacena/calcula en el backend.
 * unidad comercial = cómo el usuario ingresa/visualiza cantidades y precios.
 * factor = cantidad de unidades internas equivalentes a 1 unidad comercial.
 *
 * Ejemplo alimento: g -> kg, factor 1000.
 */

function factorValido(factor: number | string | null | undefined): number | null {
  const numero = Number(factor);
  return Number.isFinite(numero) && numero > 0 ? numero : null;
}

function esGramo(simbolo: string | null | undefined): boolean {
  const normalizado = (simbolo ?? "").trim().toLowerCase();
  return normalizado === "g" || normalizado === "gramo" || normalizado === "gramos";
}

export function unidadPresentacion(
  simboloInterno: string | null | undefined,
  simboloComercial?: string | null,
): string {
  return simboloComercial?.trim() || (esGramo(simboloInterno) ? "kg" : (simboloInterno ?? ""));
}

export function cantidadParaPresentacion(
  valor: number | string | null | undefined,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  const conversion = factorValido(factor);
  if (conversion) return numero / conversion;
  return esGramo(simboloInterno) ? numero / 1000 : numero;
}

export function cantidadDesdePresentacion(
  valor: number | string,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return numero;
  const conversion = factorValido(factor);
  if (conversion) return numero * conversion;
  return esGramo(simboloInterno) ? numero * 1000 : numero;
}

/** Precio expresado por la unidad comercial que ve el usuario. */
export function precioParaPresentacion(
  valor: number | string | null | undefined,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  const conversion = factorValido(factor);
  if (conversion) return numero * conversion;
  return esGramo(simboloInterno) ? numero * 1000 : numero;
}

/** Precio expresado por la unidad interna que espera el backend. */
export function precioDesdePresentacion(
  valor: number | string,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return numero;
  const conversion = factorValido(factor);
  if (conversion) return numero / conversion;
  return esGramo(simboloInterno) ? numero / 1000 : numero;
}

export function cantidadConUnidad(
  valor: number | string | null | undefined,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
  simboloComercial?: string | null,
  options?: Intl.NumberFormatOptions,
): string {
  const cantidad = cantidadParaPresentacion(valor, simboloInterno, factor);
  const unidad = unidadPresentacion(simboloInterno, simboloComercial);
  const texto = cantidad.toLocaleString("es-CO", options ?? { maximumFractionDigits: 3 });
  return unidad ? `${texto} ${unidad}` : texto;
}

export function precioConUnidad(
  valor: number | string | null | undefined,
  simboloInterno: string | null | undefined,
  factor?: number | string | null,
  simboloComercial?: string | null,
  options?: Intl.NumberFormatOptions,
): string {
  const precio = precioParaPresentacion(valor, simboloInterno, factor);
  const unidad = unidadPresentacion(simboloInterno, simboloComercial);
  const texto = precio.toLocaleString("es-CO", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    ...options,
  });
  return unidad ? `$ ${texto} / ${unidad}` : `$ ${texto}`;
}
