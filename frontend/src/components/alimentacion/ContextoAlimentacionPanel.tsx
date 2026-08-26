import type { ReactNode } from "react";
import { formatNumber } from "../../utils/format";
import { etiquetaRacionesCatalogo } from "../../utils/semanaReferencia";
import type { ReferenciaAlimentacionActiva } from "../../types/analisis";

type Props = {
  ref: ReferenciaAlimentacionActiva;
  /** Título del bloque (modal vs ficha). */
  titulo?: string;
};

function nd(valor: string | null | undefined): string {
  return valor ? valor : "N/D — Sin referencia configurada.";
}

export function etiquetaPesoUtilizado(
  peso: ReferenciaAlimentacionActiva["peso_utilizado"],
): string | null {
  if (peso === "real") return "Peso utilizado: última biometría (operativo)";
  if (peso === "inicial") return "Peso utilizado: inicial/operativo";
  if (peso === "esperado") return "Peso utilizado: esperado";
  return null;
}

function Fila({
  termino,
  valor,
}: {
  termino: string;
  valor: ReactNode;
}) {
  return (
    <div>
      <dt className="text-[var(--bf-muted)]">{termino}</dt>
      <dd className="mt-0.5 text-[var(--bf-ink)]">{valor}</dd>
    </div>
  );
}

function dualLinea(principal: string, secundaria?: string) {
  return (
    <span className="block">
      <span className="font-medium">{principal}</span>
      {secundaria ? <span className="mt-0.5 block text-[var(--bf-muted)]">{secundaria}</span> : null}
    </span>
  );
}

function textoCantidadPorRacion(ref: ReferenciaAlimentacionActiva): ReactNode {
  const rango =
    ref.racion_por_comida_min_g != null &&
    ref.racion_por_comida_max_g != null &&
    ref.racion_por_comida_min_kg != null &&
    ref.racion_por_comida_max_kg != null;
  if (rango) {
    return dualLinea(
      `${formatNumber(ref.racion_por_comida_min_g, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}–${formatNumber(ref.racion_por_comida_max_g, { maximumFractionDigits: 1, minimumFractionDigits: 1 })} g/ración`,
      `${formatNumber(ref.racion_por_comida_min_kg, { maximumFractionDigits: 4, minimumFractionDigits: 4 })}–${formatNumber(ref.racion_por_comida_max_kg, { maximumFractionDigits: 4, minimumFractionDigits: 4 })} kg/ración`,
    );
  }
  if (ref.racion_por_comida_kg != null) {
    const kg = `${formatNumber(ref.racion_por_comida_kg, { maximumFractionDigits: 3, minimumFractionDigits: 3 })} kg/ración`;
    const g =
      ref.racion_por_comida_g != null
        ? `${formatNumber(ref.racion_por_comida_g, { maximumFractionDigits: 0 })} g/ración`
        : undefined;
    return dualLinea(kg, g);
  }
  return "N/D";
}

/** Campos oficiales de ración: solo formatea lo que entrega el backend. */
export function CamposAlimentacionRecomendada({ ref }: { ref: ReferenciaAlimentacionActiva }) {
  const pesoOperativo =
    ref.peso_operativo_g ?? ref.peso_para_racion_g ?? ref.peso_inicial_g;
  const raciones = etiquetaRacionesCatalogo(ref.raciones_min, ref.raciones_max, ref.raciones_diarias);

  return (
    <dl className="grid gap-2 sm:grid-cols-2 text-xs">
      <Fila
        termino="Peso operativo"
        valor={
          pesoOperativo != null
            ? `${formatNumber(pesoOperativo, { maximumFractionDigits: 2, minimumFractionDigits: 2 })} g`
            : "N/D"
        }
      />
      <Fila
        termino="Peso esperado"
        valor={
          ref.peso_esperado_g != null
            ? `${formatNumber(ref.peso_esperado_g, { maximumFractionDigits: 2, minimumFractionDigits: 2 })} g`
            : "N/D — Sin referencia configurada."
        }
      />
      {ref.diferencia_peso_g != null ? (
        <Fila
          termino="Diferencia"
          valor={`${formatNumber(ref.diferencia_peso_g, { maximumFractionDigits: 2, minimumFractionDigits: 2, signDisplay: "exceptZero" })} g`}
        />
      ) : null}
      <Fila termino="Peces vivos" valor={formatNumber(ref.poblacion_estimada)} />
      <Fila
        termino="Biomasa para ración"
        valor={
          ref.biomasa_para_racion_kg != null
            ? `${formatNumber(ref.biomasa_para_racion_kg, { maximumFractionDigits: 3 })} kg`
            : "N/D"
        }
      />
      <Fila
        termino="Tasa"
        valor={
          ref.tasa_alimentacion_pct != null
            ? `${formatNumber(ref.tasa_alimentacion_pct, { maximumFractionDigits: 1 })} %/día`
            : "N/D — Sin referencia configurada."
        }
      />
      <Fila
        termino="Alimento recomendado"
        valor={
          ref.racion_diaria_recomendada_kg != null
            ? dualLinea(
                `${formatNumber(ref.racion_diaria_recomendada_kg, { maximumFractionDigits: 3 })} kg/día`,
                ref.racion_diaria_recomendada_g != null
                  ? `${formatNumber(ref.racion_diaria_recomendada_g, { maximumFractionDigits: 1 })} g/día`
                  : undefined,
              )
            : "N/D — Sin referencia configurada."
        }
      />
      <Fila
        termino="Raciones recomendadas"
        valor={raciones === "N/D" ? "N/D — Sin referencia configurada." : raciones}
      />
      <Fila termino="Cantidad por ración" valor={textoCantidadPorRacion(ref)} />
    </dl>
  );
}

/**
 * Panel de alimentación recomendada antes de registrar.
 * Escala la referencia biológica (tasa/raciones) a la población viva y el peso operativo del lote.
 */
export function ContextoAlimentacionPanel({ ref, titulo = "Alimentación recomendada" }: Props) {
  const pesoUtilizado = etiquetaPesoUtilizado(ref.peso_utilizado);

  return (
    <div className="rounded-xl border border-[var(--bf-border)] bg-[var(--bf-surface)] p-3 text-sm">
      <p className="mb-3 font-display text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">
        {titulo}
      </p>
      <p className="mb-3 font-medium text-[var(--bf-ink)]">
        Semana {ref.semana_productiva} · {nd(ref.fase)}
      </p>
      <CamposAlimentacionRecomendada ref={ref} />
      {pesoUtilizado ? (
        <p className="mt-3 text-xs text-[var(--bf-muted)]">{pesoUtilizado}.</p>
      ) : null}
    </div>
  );
}
