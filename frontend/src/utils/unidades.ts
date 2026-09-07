/**
 * Convenciones de presentación para inventario y alimentación.
 *
 * El backend conserva la unidad registrada en el producto y todas sus
 * cantidades/fórmulas. Para productos cuya unidad interna es gramos (g),
 * la interfaz de usuario trabaja en kilogramos (kg), que es la unidad
 * comercial habitual del alimento.
 *
 * Regla de conversión:
 *   1 kg = 1.000 g
 *
 * Estas funciones NO cambian datos almacenados; solo convierten los valores
 * al entrar/salir de la interfaz.
 */

function esGramo(simbolo: string | null | undefined): boolean {
  const normalizado = (simbolo ?? "").trim().toLowerCase();
  return normalizado === "g" || normalizado === "gramo" || normalizado === "gramos";
}

export function unidadPresentacion(simbolo: string | null | undefined): string {
  return esGramo(simbolo) ? "kg" : (simbolo ?? "");
}

export function cantidadParaPresentacion(
  valor: number | string | null | undefined,
  simbolo: string | null | undefined,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  return esGramo(simbolo) ? numero / 1000 : numero;
}

export function cantidadDesdePresentacion(
  valor: number | string,
  simbolo: string | null | undefined,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return numero;
  return esGramo(simbolo) ? numero * 1000 : numero;
}

/** Precio expresado por la unidad que ve el usuario. */
export function precioParaPresentacion(
  valor: number | string | null | undefined,
  simbolo: string | null | undefined,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 0;
  // Si el backend guarda $/g, la pantalla muestra $/kg.
  return esGramo(simbolo) ? numero * 1000 : numero;
}

/** Precio expresado por la unidad interna que espera el backend. */
export function precioDesdePresentacion(
  valor: number | string,
  simbolo: string | null | undefined,
): number {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return numero;
  // Si el usuario escribe $/kg, el backend recibe el equivalente $/g.
  return esGramo(simbolo) ? numero / 1000 : numero;
}

export function cantidadConUnidad(
  valor: number | string | null | undefined,
  simbolo: string | null | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  const cantidad = cantidadParaPresentacion(valor, simbolo);
  const unidad = unidadPresentacion(simbolo);
  const texto = cantidad.toLocaleString("es-CO", options ?? {
    maximumFractionDigits: 3,
  });
  return unidad ? `${texto} ${unidad}` : texto;
}

export function precioConUnidad(
  valor: number | string | null | undefined,
  simbolo: string | null | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  const precio = precioParaPresentacion(valor, simbolo);
  const unidad = unidadPresentacion(simbolo);
  const texto = precio.toLocaleString("es-CO", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    ...options,
  });
  return unidad ? `$ ${texto} / ${unidad}` : `$ ${texto}`;
}
