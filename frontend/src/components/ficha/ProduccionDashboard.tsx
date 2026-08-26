import { useMemo, type ReactNode } from "react";
import { ChartCard } from "../charts/ChartCard";
import { ComparativeLineChart } from "../charts/ComparativeLineChart";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { ReferenciaVsLoteReal } from "../alimentacion/ReferenciaVsLoteReal";
import { formatDate, formatDateTime, formatNumber } from "../../utils/format";
import {
  badgePesoVsEsperado,
  fechaLocalISO,
  mortalidadDiariaPromedio,
  num,
  PESO_OBJETIVO_COSECHA_G,
  proyectarCosecha,
  racionSobreBiomasaPct,
} from "../../utils/indicadoresProduccion";
import { buscarEvaluacion, colorSerieRealEvaluacion } from "../../utils/analisisStatus";
import { toNumber, type PuntoComparativo } from "../../utils/series";
import type { AnalisisLote } from "../../types/analisis";
import { FichaBadge, FichaCard, FichaMetric, FichaSectionHeader } from "./FichaMetric";
import {
  FCA_DEFINICION,
  FCA_ESPERADO_ND,
  FCA_HINT_ECONOMICO,
  FCA_LABEL,
  FCA_SERIE_DESCRIPCION,
  FCA_SERIE_TITULO,
  FCA_UNIDAD,
  fcaPeriodoHint,
} from "../../utils/fcaPresentacion";

function fmtInt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "N/D";
  return formatNumber(value, { maximumFractionDigits: 0 });
}

function fmtDec(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "N/D";
  return formatNumber(value, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function PanelSimple({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
      <h3 className="font-display text-sm font-semibold text-[var(--bf-ink)]">{title}</h3>
      {hint ? <p className="mt-1 text-xs text-[var(--bf-muted)]">{hint}</p> : null}
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function ProduccionDashboard({ data }: { data: AnalisisLote }) {
  const ind = data.indicadores;
  const refAlim = data.referencia_alimentacion;
  const comparacion = data.comparaciones.peso_g;
  const pesoEsperado = num(refAlim?.peso_esperado_g ?? data.referencia_produccion?.peso_esperado_g);
  const pesoActual = num(ind.peso_promedio_g);
  const densidad = num(ind.densidad_kg_m3);
  const volumen = num(ind.volumen_util_m3);
  const sgr = num(ind.sgr_pct_dia);
  const mortDiaria = mortalidadDiariaPromedio(ind.mortalidad_acumulada, ind.dias_cultivo);
  const diffPct = num(comparacion.diferencia_porcentaje);
  const badgePeso = badgePesoVsEsperado(diffPct);
  const racion = num(ind.racion_diaria_recomendada_kg);
  const biomasaOperativa = num(refAlim?.biomasa_para_racion_kg);
  const tasaSobreBiomasa = racionSobreBiomasaPct(racion, biomasaOperativa);
  const proyeccion = proyectarCosecha({
    fechaSiembra: data.lote.fecha_siembra,
    diasCultivo: ind.dias_cultivo,
    pesoActualG: pesoActual,
    gananciaDiariaG: num(ind.ganancia_diaria_g),
    poblacion: ind.poblacion_estimada,
  });

  const badgeProduccion = badgePeso
    ? { label: badgePeso.label, tone: badgePeso.tone }
    : null;

  const puntosPeso = useMemo(
    (): PuntoComparativo[] =>
      data.biometrias.map((fila) => ({
        etiqueta: `S${fila.semana_cultivo} · ${formatDate(fila.fecha_hora)}`,
        real: toNumber(fila.peso_promedio_g),
        esperado: toNumber(fila.peso_esperado_g),
        minimo: null,
        maximo: null,
        objetivo: null,
      })),
    [data.biometrias],
  );

  const evalPeso = buscarEvaluacion(data.evaluaciones, "peso_promedio_g");

  const puntosFca = useMemo(
    () =>
      data.serie_fca
        .filter((fila) => fila.fca != null)
        .map((fila) => ({
          etiqueta: formatDateTime(fila.fecha_hora),
          fca: toNumber(fila.fca),
        })),
    [data.serie_fca],
  );

  const serieAlim = data.serie_alimentacion_comparativa ?? [];
  const puntosAlim = useMemo(
    (): PuntoComparativo[] =>
      serieAlim.map((punto) => ({
        etiqueta: formatDate(punto.fecha),
        real: toNumber(punto.real_kg),
        recomendado: toNumber(punto.recomendada_kg),
        minimo: null,
        maximo: null,
        objetivo: null,
      })),
    [serieAlim],
  );
  const evalAlim = buscarEvaluacion(data.evaluaciones, "alimentacion_diaria_kg");

  return (
    <section className="border-t-4 border-[var(--bf-bg)] bg-[color-mix(in_srgb,var(--bf-accent-soft)_55%,white)] px-6 py-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-extrabold text-[var(--bf-ink)]">Producción</h2>
        {badgeProduccion ? <FichaBadge tone={badgeProduccion.tone}>{badgeProduccion.label}</FichaBadge> : null}
      </div>

      <FichaCard>
        <FichaSectionHeader
          title="Crecimiento"
          note={data.lote.codigo ? `vs. referencia ${data.especie.nombre_comun}` : undefined}
        />
        <div className="mb-5 grid grid-cols-2 gap-5 md:grid-cols-4">
          <FichaMetric label="Ganancia de peso" value={fmtDec(num(ind.ganancia_peso_g), 2)} unit="g" />
          <FichaMetric label="Ganancia diaria" value={fmtDec(num(ind.ganancia_diaria_g), 2)} unit="g/día" />
          <FichaMetric label="Tasa de crec. específica (SGR)" value={fmtDec(sgr, 2)} unit="%/día" />
          <FichaMetric
            label="Peso real vs. esperado"
            value={diffPct == null ? "N/D" : `${diffPct > 0 ? "+" : ""}${fmtDec(diffPct, 1)}`}
            unit={diffPct == null ? undefined : "%"}
            sub={`Esperado: ${fmtDec(pesoEsperado, 1)} g · Real: ${fmtDec(pesoActual, 1)} g`}
            badge={badgePeso ? <FichaBadge tone={badgePeso.tone}>{badgePeso.label}</FichaBadge> : undefined}
          />
          <FichaMetric
            label="Ganancia de biomasa"
            value={fmtDec(num(data.productividad.ganancia_biomasa_kg), 2)}
            unit="kg"
            sub={data.productividad.motivos.ganancia_biomasa_kg ?? undefined}
          />
          <FichaMetric
            label="Peso cosechado"
            value={fmtDec(num(data.productividad.peso_cosechado_kg), 3)}
            unit="kg"
          />
          <FichaMetric
            label="Talla promedio"
            value={fmtDec(num(ind.talla_promedio), 2)}
            unit={ind.unidad_talla ?? undefined}
            sub={ind.talla_promedio == null ? "SIN_TALLA" : undefined}
          />
          <FichaMetric
            label="Densidad actual"
            value={fmtDec(densidad, 1)}
            unit={densidad == null ? undefined : "kg/m³"}
            sub={
              volumen == null
                ? "N/D — sin volumen útil del estanque"
                : `Volumen útil ${fmtDec(volumen, 2)} m³`
            }
          />
          <FichaMetric label="Mortalidad diaria prom." value={fmtDec(mortDiaria, 1)} unit="peces/día" />
          <FichaMetric
            label="Uniformidad (CV)"
            value="N/D"
            sub="Sin pesos individuales de la muestra"
          />
        </div>
        {puntosPeso.length >= 1 ? (
          <ChartCard
            title="Peso real vs peso esperado"
            unidad="g"
            descripcion="Cada biometría usa el peso esperado de su propia semana de cultivo."
            vacio={puntosPeso.length === 0}
            vacioMensaje="Sin biometrías en el ciclo."
          >
            <ComparativeLineChart
              data={puntosPeso}
              unidad="g"
              colorReal={colorSerieRealEvaluacion(evalPeso)}
              digitos={2}
              mostrarBandaRango={false}
              altura={224}
            />
          </ChartCard>
        ) : (
          <p className="text-sm text-[var(--bf-muted)]">N/D — sin biometrías para graficar el crecimiento.</p>
        )}
      </FichaCard>

      <FichaCard>
        <FichaSectionHeader title="Alimentación y eficiencia" />
        <div className="mb-5 grid grid-cols-2 gap-5 md:grid-cols-4">
          <FichaMetric
            label="Alimento real acumulado"
            value={fmtDec(num(ind.alimento_real_acumulado_kg), 1)}
            unit="kg"
            sub={data.pendientes.alimento_real_acumulado_kg ?? undefined}
          />
          <FichaMetric
            label="Biomasa neta (denominador FCA)"
            value={fmtDec(num(data.eficiencia.ganancia_biomasa_kg), 2)}
            unit="kg"
            sub="biomasa actual + cosechada − inicial"
          />
          <FichaMetric
            label={FCA_LABEL}
            value={
              ind.fca_disponible
                ? formatNumber(ind.fca, { minimumFractionDigits: 4, maximumFractionDigits: 4 })
                : "N/D"
            }
            unit={ind.fca_disponible ? "kg/kg" : undefined}
            sub={
              ind.fca_disponible
                ? `${FCA_UNIDAD}. ${fcaPeriodoHint(data.lote.fecha_cierre)}`
                : (ind.fca_motivo ?? "N/D")
            }
          />
          <FichaMetric
            label="Ración sobre biomasa"
            value={fmtDec(tasaSobreBiomasa, 1)}
            unit="%"
            sub="Sobre biomasa operativa. No es biomasa actual."
          />
          <FichaMetric
            label="Costo por kg"
            value={data.eficiencia.costo_por_kg == null ? "N/D" : fmtDec(num(data.eficiencia.costo_por_kg), 2)}
            sub={data.eficiencia.costo_por_kg_motivo ?? undefined}
          />
          <FichaMetric
            label="Costo de alimentación"
            value={data.eficiencia.costo_alimentacion == null ? "N/D" : fmtDec(num(data.eficiencia.costo_alimentacion), 2)}
            sub={data.eficiencia.costo_alimentacion_motivo ?? undefined}
          />
        </div>

        {data.referencia_alimentacion ? <ReferenciaVsLoteReal data={data} Panel={PanelSimple} /> : null}

        {puntosAlim.length >= 2 ? (
          <div className="mt-4">
            <ChartCard
              title="Alimentación real vs recomendada"
              unidad="kg"
              descripcion="La recomendada se recálcula por día con semana, población viva, peso y tasa."
            >
              <ComparativeLineChart
                data={puntosAlim}
                unidad="kg"
                colorReal={colorSerieRealEvaluacion(evalAlim)}
                digitos={3}
                mostrarBandaRango={false}
                altura={224}
              />
            </ChartCard>
          </div>
        ) : (
          <p className="mt-3 text-sm text-[var(--bf-muted)]">
            Gráfica de alimentación: se muestra con al menos dos días de registros convertibles a kg.
          </p>
        )}

        {puntosFca.length >= 2 ? (
          <div className="mt-4">
            <ChartCard
              title={FCA_SERIE_TITULO}
              unidad=""
              descripcion={FCA_SERIE_DESCRIPCION}
            >
              <TimeSeriesChart
                data={puntosFca}
                series={[{ key: "fca", nombre: FCA_LABEL }]}
                digitos={4}
                altura={224}
              />
            </ChartCard>
            <p className="mt-2 text-xs text-[var(--bf-muted)]" title={FCA_HINT_ECONOMICO}>
              {FCA_DEFINICION} {FCA_ESPERADO_ND}
            </p>
          </div>
        ) : (
          <div className="mt-4">
            <p className="text-sm text-[var(--bf-muted)]" title={FCA_HINT_ECONOMICO}>
              {FCA_DEFINICION} {fcaPeriodoHint(data.lote.fecha_cierre)} {FCA_HINT_ECONOMICO}
            </p>
            <p className="mt-2 text-xs text-[var(--bf-muted)]">{FCA_ESPERADO_ND}</p>
          </div>
        )}
      </FichaCard>

      <FichaCard>
        <FichaSectionHeader title="Proyección de cosecha" />
        <div className="grid grid-cols-2 gap-5 md:grid-cols-3">
          <FichaMetric
            label="Objetivo de peso"
            value={fmtInt(proyeccion.objetivoPesoG)}
            unit="g"
          />
          <FichaMetric
            label="Fecha máxima de ciclo"
            value={
              proyeccion.fechaMaximaCiclo
                ? formatDate(fechaLocalISO(proyeccion.fechaMaximaCiclo))
                : "N/D"
            }
            sub="Calendario de 24 semanas. No es predicción de crecimiento."
          />
          <FichaMetric
            label="Cosecha estimada"
            value={
              proyeccion.fechaCosechaEstimada
                ? formatDate(fechaLocalISO(proyeccion.fechaCosechaEstimada))
                : "N/D"
            }
            sub={
              proyeccion.usaPrediccionCrecimiento
                ? proyeccion.nota
                : "Sin peso real y GPD válidos: no hay predicción de crecimiento."
            }
          />
        </div>
        <div className="mt-5 grid grid-cols-2 gap-5 md:grid-cols-4">
          <FichaMetric
            label={
              proyeccion.usaPrediccionCrecimiento
                ? "Días restantes (crecimiento)"
                : "Días restantes (calendario)"
            }
            value={
              proyeccion.usaPrediccionCrecimiento
                ? proyeccion.diasRestantesCrecimiento == null
                  ? "N/D"
                  : fmtInt(proyeccion.diasRestantesCrecimiento)
                : fmtInt(proyeccion.diasRestantesCalendario)
            }
            unit="días"
          />
          <FichaMetric
            label="Peso proyectado a cosecha"
            value={fmtDec(proyeccion.pesoProyectadoG, 0)}
            unit="g"
            sub={
              proyeccion.pesoProyectadoG == null
                ? "Sin GPD para proyectar"
                : `Objetivo comercial ${PESO_OBJETIVO_COSECHA_G} g`
            }
          />
          <FichaMetric label="Biomasa proyectada" value={fmtDec(proyeccion.biomasaProyectadaKg, 1)} unit="kg" />
        </div>
      </FichaCard>
    </section>
  );
}
