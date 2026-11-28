import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listReferenciasAplicacionBiofloc } from "../../api/catalogs";
import { listProductosActivos } from "../../api/operations";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { formatNumber } from "../../utils/format";
import type { Lote } from "../../types/production";

function semanaProductiva(fechaSiembra: string): number {
  const fecha = fechaSiembra.slice(0, 10).split("-").map(Number);
  const inicio = Date.UTC(fecha[0], fecha[1] - 1, fecha[2]);
  const ahora = new Date();
  const hoy = Date.UTC(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());
  return Math.max(1, Math.floor(Math.max(0, hoy - inicio) / 604800000) + 1);
}

export function ReferenciaSemanalBioflocPanel({ lote }: { lote: Lote }) {
  const semana = semanaProductiva(lote.fecha_siembra);
  const referenciasQuery = useQuery({
    queryKey: ["referencias-aplicacion-biofloc", lote.especie_id, semana, true],
    queryFn: () => listReferenciasAplicacionBiofloc({
      especie_id: lote.especie_id,
      semana,
      solo_activos: true,
    }),
    enabled: semana <= 20,
  });
  const productosQuery = useQuery({
    queryKey: ["productos-activos", "referencias-biofloc"],
    queryFn: listProductosActivos,
  });
  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((producto) => [producto.id, producto])),
    [productosQuery.data],
  );
  const referencias = referenciasQuery.data ?? [];

  return (
    <section className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">
            Referencia semanal de insumos Biofloc
          </h2>
          <p className="mt-1 text-sm text-[var(--bf-muted)]">
            Lote {lote.codigo} · Semana productiva {semana} de 20
          </p>
        </div>
        <span className="rounded-full border border-[var(--bf-border)] px-3 py-1 text-xs text-[var(--bf-muted)]">
          {semana >= 1 && semana <= 4 ? "Inicio" : semana <= 10 ? "Levante" : semana <= 20 ? "Engorde" : "Ciclo terminado"}
        </span>
      </div>

      {semana > 20 ? (
        <p className="mt-4 text-sm text-[var(--bf-muted)]">
          El lote superó las 20 semanas contempladas en el catálogo de referencias. No se extrapolan cantidades.
        </p>
      ) : null}
      {semana <= 20 && referenciasQuery.isLoading ? <LoadingState label="Consultando referencias del catálogo…" /> : null}
      {referenciasQuery.isError ? <ErrorAlert message="No fue posible consultar las referencias semanales de Biofloc." /> : null}
      {productosQuery.isError ? <ErrorAlert message="No fue posible consultar los nombres de los insumos." /> : null}

      {semana <= 20 && !referenciasQuery.isLoading && !referenciasQuery.isError && referencias.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-[var(--bf-border)] p-4 text-sm text-[var(--bf-muted)]">
          No hay referencias activas configuradas para esta especie y semana. No se generan cantidades estimadas.
        </p>
      ) : null}

      {referencias.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--bf-border)] text-xs text-[var(--bf-muted)]">
                <th className="px-3 py-2 font-medium">Insumo</th>
                <th className="px-3 py-2 font-medium">Cantidad de referencia</th>
                <th className="px-3 py-2 font-medium">Base de peces</th>
                <th className="px-3 py-2 font-medium">Biomasa objetivo</th>
              </tr>
            </thead>
            <tbody>
              {referencias.map((referencia) => (
                <tr key={referencia.id} className="border-b border-[var(--bf-border)] last:border-0">
                  <td className="px-3 py-3 font-medium text-[var(--bf-ink)]">
                    {productos.get(referencia.producto_id)?.nombre ?? `Producto #${referencia.producto_id}`}
                  </td>
                  <td className="px-3 py-3 tabular-nums">
                    {formatNumber(referencia.cantidad_referencia, { maximumFractionDigits: 4 })} {referencia.unidad}
                  </td>
                  <td className="px-3 py-3 tabular-nums">{formatNumber(referencia.base_peces)} peces</td>
                  <td className="px-3 py-3 tabular-nums">
                    {referencia.biomasa_objetivo_kg == null
                      ? "N/D"
                      : `${formatNumber(referencia.biomasa_objetivo_kg, { maximumFractionDigits: 3 })} kg`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="mt-3 rounded-lg border border-amber-300/50 bg-amber-50/50 px-3 py-2 text-xs text-amber-900">
        Estas cantidades son referencias presupuestales del catálogo, asociadas a una base de peces y biomasa objetivo.
        No son una dosis automática ni una orden de aplicación. Valide mediciones actuales y ficha técnica antes de aplicar.
      </p>
    </section>
  );
}
