import { formatDateTime, formatNumber } from "../../utils/format";
import { etiquetaRacionesCatalogo } from "../../utils/semanaReferencia";
import type { AnalisisLote, ApiDecimal, ReferenciaAlimentacionActiva } from "../../types/analisis";
import { etiquetaPesoUtilizado } from "./ContextoAlimentacionPanel";

function Fila({ termino, valor, detalle }: { termino: string; valor: string; detalle?: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{termino}</dt>
      <dd className="mt-0.5 font-medium text-[var(--bf-ink)]">{valor}</dd>
      {detalle ? <p className="mt-0.5 text-xs text-[var(--bf-muted)]">{detalle}</p> : null}
    </div>
  );
}

function kgApi(valor: ApiDecimal | null | undefined, digitos = 3): string | null {
  if (valor == null || valor === "") return null;
  return `${formatNumber(valor, { maximumFractionDigits: digitos, minimumFractionDigits: digitos })} kg`;
}

function gApi(valor: ApiDecimal | null | undefined): string | null {
  if (valor == null || valor === "") return null;
  return `${formatNumber(valor, { maximumFractionDigits: 2, minimumFractionDigits: 2 })} g`;
}

function bloqueReferencia(ref: ReferenciaAlimentacionActiva) {
  return (
    <>
      <Fila termino="Semana" valor={String(ref.semana_productiva)} />
      <Fila
        termino="Peso operativo"
        valor={
          (ref.peso_operativo_g ?? ref.peso_para_racion_g) != null
            ? `${formatNumber(ref.peso_operativo_g ?? ref.peso_para_racion_g, { maximumFractionDigits: 2 })} g`
            : "N/D"
        }
      />
      <Fila
        termino="Peso esperado"
        valor={
          ref.peso_esperado_g != null
            ? `${formatNumber(ref.peso_esperado_g, { maximumFractionDigits: 2 })} g`
            : "N/D — Sin referencia configurada."
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
        termino="Raciones"
        valor={
          etiquetaRacionesCatalogo(ref.raciones_min, ref.raciones_max, ref.raciones_diarias) === "N/D"
            ? "N/D — Sin referencia configurada."
            : etiquetaRacionesCatalogo(ref.raciones_min, ref.raciones_max, ref.raciones_diarias)
        }
      />
      <Fila
        termino="Peso utilizado"
        valor={etiquetaPesoUtilizado(ref.peso_utilizado) ?? "N/D"}
      />
    </>
  );
}

function alimentoRealUltimoDia(data: AnalisisLote): string {
  const porDia = new Map<string, number>();
  for (const fila of data.alimentacion_real) {
    if (fila.cantidad_kg == null) continue;
    const dia = fila.fecha_hora.slice(0, 10);
    porDia.set(dia, (porDia.get(dia) ?? 0) + Number(fila.cantidad_kg));
  }
  const ultimo = [...porDia.entries()].at(-1);
  if (!ultimo) return "N/D — sin alimentación registrada";
  return `${formatNumber(ultimo[1], { maximumFractionDigits: 3 })} kg/día`;
}

type ReferenciaVsLoteRealProps = {
  data: AnalisisLote;
  Panel: (props: { title: string; hint?: string; children: React.ReactNode }) => React.ReactNode;
};

/** Referencia biológica de la semana vs estado real del lote (escalado por población). */
export function ReferenciaVsLoteReal({ data, Panel }: ReferenciaVsLoteRealProps) {
  const ref = data.referencia_alimentacion;
  const ind = data.indicadores;
  if (!ref) return null;

  const porDia = new Map<string, number>();
  for (const fila of data.alimentacion_real) {
    if (fila.cantidad_kg == null) continue;
    const dia = fila.fecha_hora.slice(0, 10);
    porDia.set(dia, (porDia.get(dia) ?? 0) + Number(fila.cantidad_kg));
  }
  const ultimoReal = [...porDia.values()].at(-1);
  const desviacionPct =
    ultimoReal != null && ind.racion_diaria_recomendada_kg != null && Number(ind.racion_diaria_recomendada_kg) !== 0
      ? `${formatNumber(
          ((ultimoReal - Number(ind.racion_diaria_recomendada_kg)) /
            Number(ind.racion_diaria_recomendada_kg)) *
            100,
          { maximumFractionDigits: 2 },
        )} %`
      : null;

  const biomasaInicial = kgApi(ind.biomasa_inicial_kg);
  const biomasaOperativa = kgApi(ref.biomasa_para_racion_kg);
  const biomasaActual = kgApi(ind.biomasa_actual_kg);
  const pesoOperativo = gApi(ref.peso_operativo_g ?? ref.peso_para_racion_g);
  const pesoBiometria = gApi(ind.peso_promedio_g);

  return (
    <Panel
      title="Referencia actual vs lote real"
      hint="La referencia es la guía (peso esperado, tasa y raciones). La ración se calcula con población viva y peso operativo (inicial o última biometría)."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">
            Referencia actual
          </h3>
          <dl className="grid gap-3 sm:grid-cols-2 text-sm">{bloqueReferencia(ref)}</dl>
        </div>
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--bf-ink)]">
            Lote real
          </h3>
          <dl className="grid gap-3 sm:grid-cols-2 text-sm">
            <Fila
              termino="Peso operativo"
              valor={
                (ref.peso_operativo_g ?? ref.peso_para_racion_g) != null
                  ? `${formatNumber(ref.peso_operativo_g ?? ref.peso_para_racion_g, { maximumFractionDigits: 2 })} g`
                  : "N/D"
              }
            />
            <Fila
              termino="Última biometría"
              valor={
                ind.peso_promedio_g != null
                  ? `${formatNumber(ind.peso_promedio_g, { maximumFractionDigits: 2 })} g`
                  : "N/D — sin biometría"
              }
            />
            <Fila termino="Población viva" valor={`${formatNumber(ind.poblacion_estimada)} peces`} />
            <Fila
              termino="Biomasa inicial"
              valor={biomasaInicial ?? "N/D"}
              detalle={
                biomasaInicial == null
                  ? (data.pendientes.biomasa_inicial_kg ?? "Sin peso inicial de siembra")
                  : undefined
              }
            />
            <Fila
              termino="Biomasa operativa"
              valor={biomasaOperativa ?? "N/D"}
              detalle={pesoOperativo ? `Peso operativo: ${pesoOperativo}` : "Sin peso operativo"}
            />
            <Fila
              termino="Biomasa actual"
              valor={biomasaActual ?? "N/D"}
              detalle={
                biomasaActual == null
                  ? "Sin biometría registrada"
                  : [
                      pesoBiometria ? `Basada en biometría de ${pesoBiometria}` : null,
                      ind.fecha_ultima_biometria ? formatDateTime(ind.fecha_ultima_biometria) : null,
                    ]
                      .filter(Boolean)
                      .join(" · ") || undefined
              }
            />
            <Fila termino="Alimento real (último día)" valor={alimentoRealUltimoDia(data)} />
            <Fila
              termino="Alimento recomendado"
              valor={
                ind.racion_diaria_recomendada_kg != null
                  ? `${formatNumber(ind.racion_diaria_recomendada_kg, { maximumFractionDigits: 3 })} kg/día`
                  : "N/D"
              }
            />
            {desviacionPct != null ? <Fila termino="Desviación" valor={desviacionPct} /> : null}
          </dl>
        </div>
      </div>
    </Panel>
  );
}
