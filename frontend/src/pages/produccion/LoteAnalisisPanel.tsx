import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAnalisisLote } from "../../api/analisis";
import { ReferenciaVsLoteReal } from "../../components/alimentacion/ReferenciaVsLoteReal";
import {
  CamposAlimentacionRecomendada,
  etiquetaPesoUtilizado,
} from "../../components/alimentacion/ContextoAlimentacionPanel";
import { RealReferenceCard } from "../../components/analisis/RealReferenceCard";
import { ProduccionDashboard } from "../../components/ficha/ProduccionDashboard";
import { etiquetaRangoSemanas, etiquetaRacionesCatalogo } from "../../utils/semanaReferencia";
import { CategoryBarChart } from "../../components/charts/CategoryBarChart";
import { ChartCard } from "../../components/charts/ChartCard";
import { ComparativeLineChart } from "../../components/charts/ComparativeLineChart";
import { TimeSeriesChart } from "../../components/charts/TimeSeriesChart";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate, formatDateTime, formatNumber } from "../../utils/format";
import {
  agruparAguaPorParametro,
  prepararBiofloc,
  prepararPuntosComparativos,
  toNumber,
  totalizarAlimentoKgPorDia,
} from "../../utils/series";
import {
  buscarEvaluacion,
  colorSerieRealEvaluacion,
  etiquetaCumplimiento,
  referenciaDesdeEvaluacion,
  tituloRecomendacion,
  toneCumplimiento,
  cumplimientoPorRango,
} from "../../utils/analisisStatus";
import type { PuntoComparativo } from "../../utils/series";
import type { AnalisisLote, AnalisisStats, ReferenciaAlimentacionActiva } from "../../types/analisis";
import {
  FCA_DEFINICION,
  FCA_ESPERADO_ND,
  FCA_HINT_ECONOMICO,
  FCA_LABEL,
  FCA_SERIE_DESCRIPCION,
  FCA_SERIE_TITULO,
  fcaHintDisponible,
  fcaHintNoDisponible,
} from "../../utils/fcaPresentacion";

type SeccionId = "resumen" | "produccion" | "agua" | "biofloc" | "alimentacion" | "referencia";

const SECCIONES: { id: SeccionId; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "produccion", label: "Producción" },
  { id: "agua", label: "Calidad de agua" },
  { id: "biofloc", label: "Biofloc" },
  { id: "alimentacion", label: "Alimentación" },
  { id: "referencia", label: "Real vs referencia" },
];

/** Traducción de los códigos técnicos que envía el backend en `pendientes`. */
const MOTIVOS: Record<string, string> = {
  SIN_BIOMETRIA: "Sin biometría registrada.",
  SIN_TALLA: "Sin talla registrada.",
  SIN_PESO_INICIAL_LOTE: "El lote no registra peso inicial promedio.",
  DIAS_CULTIVO_CERO: "El lote se sembró hoy: todavía no hay días de cultivo.",
  SIN_ALIMENTO_REAL_REGISTRADO: "Sin alimentación registrada.",
  UNIDAD_ALIMENTO_INCOMPATIBLE:
    "Hay alimento en una unidad que no es de masa: no se puede totalizar en kg.",
  SIN_BIOMASA_INICIAL: "Sin biomasa inicial disponible.",
  SIN_BIOMASA_FINAL: "Sin biomasa final disponible.",
  GANANCIA_BIOMASA_NO_POSITIVA: "La biomasa no creció respecto a la siembra.",
  SIN_REFERENCIA_PRODUCCION_APLICABLE: "N/D — Sin referencia configurada.",
  REFERENCIA_SIN_TASA_ALIMENTACION: "La referencia no define tasa de alimentación.",
  REFERENCIA_SIN_PESO_ESPERADO: "La referencia no define peso esperado.",
  SIN_CONFIGURACION_DE_RACIONES: "N/D — Sin referencia configurada.",
  RACIONES_EN_RANGO: "La referencia indica un rango de raciones; no se usa un único número.",
  OBJETIVO_CERO: "El objetivo es 0: no se calcula diferencia porcentual.",
  SERIE_VACIA: "Sin datos en la serie.",
  SERIE_CON_UN_SOLO_PUNTO: "Una sola medición: no permite analizar evolución.",
  PRIMER_VALOR_CERO: "El primer valor es 0: no se calcula variación porcentual.",
  COSTOS_INCOMPLETOS_SIN_PRORRATEOS:
    "Solo hay gastos directamente imputados; faltan costos trazables de alimentación, energía y otros recursos.",
  ALIMENTACION_SIN_COSTO_UNITARIO_TRAZABLE:
    "La alimentación registrada no conserva un costo unitario imputable al lote.",
  UTILIDAD_NO_DISPONIBLE_POR_COSTOS_INCOMPLETOS:
    "No se calcula utilidad ni margen porque los costos del lote no están completos.",
  COSECHA_SIN_PESO_REGISTRADO: "Hay cosecha sin peso registrado: no se inventa biomasa cosechada.",
  SGR_REQUIERE_PESOS_POSITIVOS_Y_DIAS: "SGR requiere peso inicial > 0, peso actual > 0 y días > 0.",
  SIN_VOLUMEN_UTIL_ESTANQUE: "N/D — sin volumen útil del estanque.",
  POBLACION_NEGATIVA_HISTORICA:
    "Este lote tiene población negativa por registros históricos (mortalidad y/o cosecha mayores que lo sembrado). No se corrige automáticamente.",
  SIN_REGLA_DE_AGREGACION_DE_FCA:
    "Actualmente no existe una regla oficial para agregar el FCA de varios lotes.",
  SIN_REFERENCIA_FCA: "FCA esperado: sin referencia oficial configurada.",
};

const ETIQUETAS_PENDIENTES: Record<string, string> = {
  biomasa_inicial_kg: "Biomasa inicial",
  biomasa_actual_kg: "Biomasa actual",
  ganancia_peso_g: "Ganancia de peso",
  ganancia_diaria_g: "Ganancia diaria",
  alimento_real_acumulado_kg: "Alimento real acumulado",
  fca: "FCA acumulado",
  sgr_pct_dia: "SGR",
  densidad_kg_m3: "Densidad",
  racion_diaria_recomendada_kg: "Ración diaria recomendada",
  numero_raciones_diarias: "Raciones por día",
  poblacion_estimada: "Población estimada",
};

function motivoTexto(codigo: string | null | undefined): string | undefined {
  if (!codigo) return undefined;
  return MOTIVOS[codigo] ?? codigo;
}

function Indicador({
  label,
  valor,
  digitos = 2,
  motivo,
  sufijo,
}: {
  label: string;
  valor: string | number | null | undefined;
  digitos?: number;
  motivo?: string | null;
  sufijo?: string;
}) {
  const numero = toNumber(valor ?? null);
  if (numero === null) {
    return <KpiCard label={label} value="N/D" hint={motivoTexto(motivo) ?? "No disponible."} />;
  }
  return (
    <KpiCard
      label={label}
      value={`${formatNumber(numero, { minimumFractionDigits: digitos, maximumFractionDigits: digitos })}${sufijo ? ` ${sufijo}` : ""}`}
      hint={motivoTexto(motivo)}
    />
  );
}

function Panel({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-[var(--bf-border)] bg-white p-4 shadow-[0_1px_2px_rgba(16,40,33,0.04)]">
      <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
        {title}
      </h3>
      {hint ? <p className="mt-1 text-xs text-[var(--bf-muted)]">{hint}</p> : null}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Definicion({ termino, texto }: { termino: string; texto: string }) {
  return (
    <div>
      <dt className="font-medium text-[var(--bf-ink)]">{termino}</dt>
      <dd>{texto}</dd>
    </div>
  );
}

function Fila({ termino, valor }: { termino: string; valor: ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[var(--bf-muted)]">{termino}</dt>
      <dd>{valor}</dd>
    </div>
  );
}

const SECCION_IDS = new Set<string>(SECCIONES.map((item) => item.id));

export function LoteAnalisisPanel({
  loteId,
  seccionFija,
  modoOperativo: modoOperativoProp,
}: {
  loteId: number;
  seccionFija?: SeccionId;
  /** Fuerza vista comparativa sin gráficas históricas "vs tiempo". */
  modoOperativo?: boolean;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const seccionParam = searchParams.get("seccion");
  const seccion: SeccionId =
    seccionFija ??
    (seccionParam && SECCION_IDS.has(seccionParam) ? (seccionParam as SeccionId) : "resumen");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  function setSeccion(siguiente: SeccionId) {
    const params = new URLSearchParams(searchParams);
    params.set("seccion", siguiente);
    setSearchParams(params, { replace: true });
  }
  const rango = { fechaDesde: desde || undefined, fechaHasta: hasta || undefined };
  const query = useQuery({
    queryKey: ["analisis-lote", loteId, desde, hasta],
    queryFn: () => getAnalisisLote(loteId, rango),
  });

  const data = query.data;
  /** Solo la ficha del estanque restringe series históricas; seccionFija no implica eso. */
  const modoOperativo = modoOperativoProp ?? false;
  const embebido = Boolean(seccionFija) || modoOperativo;

  return (
    <div className="space-y-4">
      {embebido ? null : (
      <p className="text-sm text-[var(--bf-muted)]">
        Los indicadores y las series las calcula el API. Este panel solo ordena, formatea y grafica: no
        recalcula biomasa, población, supervivencia, FCA acumulado, ganancia ni ración.
      </p>
      )}

      {embebido ? null : (
      <section className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-[var(--bf-muted)]">
            Desde
            <input
              type="date"
              value={desde}
              max={hasta || undefined}
              onChange={(evento) => setDesde(evento.target.value)}
              className="mt-1 block rounded-lg border border-[var(--bf-border)] px-2 py-1 text-sm text-[var(--bf-ink)]"
            />
          </label>
          <label className="text-xs text-[var(--bf-muted)]">
            Hasta
            <input
              type="date"
              value={hasta}
              min={desde || undefined}
              onChange={(evento) => setHasta(evento.target.value)}
              className="mt-1 block rounded-lg border border-[var(--bf-border)] px-2 py-1 text-sm text-[var(--bf-ink)]"
            />
          </label>
          {desde || hasta ? (
            <button
              type="button"
              className="rounded-full border border-[var(--bf-border)] px-3 py-1 text-xs text-[var(--bf-muted)] hover:text-[var(--bf-ink)]"
              onClick={() => {
                setDesde("");
                setHasta("");
              }}
            >
              Ver todo el ciclo
            </button>
          ) : null}
        </div>
        <p className="mt-2 text-xs text-[var(--bf-muted)]">
          {data?.filtros.nota ??
            "El rango recorta solo las series mostradas; los indicadores se calculan con todo el ciclo."}
        </p>
      </section>
      )}

      {embebido ? null : (
      <div className="flex flex-wrap gap-2">
        {SECCIONES.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              seccion === item.id
                ? "bg-[var(--bf-accent)] text-white"
                : "border border-[var(--bf-border)] text-[var(--bf-muted)] hover:text-[var(--bf-ink)]"
            }`}
            onClick={() => setSeccion(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      )}

      {query.isLoading ? <LoadingState label="Cargando análisis…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}

      {data ? (
        <>
          {seccion === "resumen" ? <SeccionResumen data={data} /> : null}
          {seccion === "produccion" ? (
            <SeccionProduccion data={data} modoOperativo={modoOperativo} />
          ) : null}
          {seccion === "agua" ? <SeccionAgua data={data} modoOperativo={modoOperativo} /> : null}
          {seccion === "biofloc" ? <SeccionBiofloc data={data} modoOperativo={modoOperativo} /> : null}
          {seccion === "alimentacion" ? <SeccionAlimentacion data={data} modoOperativo={modoOperativo} /> : null}
          {seccion === "referencia" ? <SeccionReferencia data={data} /> : null}
        </>
      ) : null}
    </div>
  );
}

function SeccionResumen({ data }: { data: AnalisisLote }) {
  const ind = data.indicadores;
  const pendientes = Object.entries(data.pendientes);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Peces sembrados" value={formatNumber(ind.peces_sembrados)} />
        <KpiCard label="Población estimada" value={formatNumber(ind.poblacion_estimada)} />
        <KpiCard label="Peces cosechados" value={formatNumber(ind.peces_cosechados)} />
        <KpiCard label="Mortalidad acumulada" value={formatNumber(ind.mortalidad_acumulada)} />
        <Indicador label="Supervivencia %" valor={ind.supervivencia_porcentaje} digitos={2} />
        <Indicador label="Mortalidad %" valor={ind.mortalidad_porcentaje} digitos={2} />
        <KpiCard label="Días de cultivo" value={formatNumber(ind.dias_cultivo)} />
        <KpiCard label="Semana" value={formatNumber(ind.semana_cultivo)} />
        <Indicador
          label="Biomasa inicial (kg)"
          valor={ind.biomasa_inicial_kg}
          digitos={2}
          motivo={data.pendientes.biomasa_inicial_kg}
        />
        <Indicador
          label="Biomasa actual (kg)"
          valor={ind.biomasa_actual_kg}
          digitos={2}
          motivo={data.pendientes.biomasa_actual_kg}
        />
        <Indicador
          label="Peso promedio (g)"
          valor={ind.peso_promedio_g}
          digitos={3}
          motivo={ind.peso_promedio_g === null ? "SIN_BIOMETRIA" : undefined}
        />
        <KpiCard
          label={FCA_LABEL}
          value={
            ind.fca == null
              ? "N/D"
              : formatNumber(ind.fca, { minimumFractionDigits: 4, maximumFractionDigits: 4 })
          }
          hint={
            ind.fca == null
              ? fcaHintNoDisponible(ind.fca_motivo)
              : fcaHintDisponible(data.lote.fecha_cierre)
          }
          title={FCA_HINT_ECONOMICO}
        />
        <Indicador
          label="Ración diaria recomendada (kg)"
          valor={ind.racion_diaria_recomendada_kg}
          digitos={3}
          motivo={data.pendientes.racion_diaria_recomendada_kg}
        />
        {ind.raciones_diarias_texto ? (
          <KpiCard
            label="Raciones por día"
            value={etiquetaRacionesCatalogo(
              data.referencia_alimentacion?.raciones_min,
              data.referencia_alimentacion?.raciones_max,
              ind.raciones_diarias_texto,
            )}
          />
        ) : (
          <Indicador
            label="Raciones por día"
            valor={ind.numero_raciones_diarias}
            digitos={0}
            motivo={data.pendientes.numero_raciones_diarias}
          />
        )}
      </div>

      <Panel title="Finanzas del lote" hint="Ingresos y gastos directamente vinculados al lote; no se prorratean costos de granja.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Ingresos vinculados" value={formatCop(data.finanzas.ingresos_lote)} hint={`${data.finanzas.ventas_registradas} venta(s)`} />
          <KpiCard label="Gastos imputados" value={formatCop(data.finanzas.gastos_directos_lote)} hint={`${data.finanzas.gastos_registrados} gasto(s)`} />
          <KpiCard label="Utilidad" value="N/D" hint={motivoTexto(data.finanzas.utilidad_motivo)} />
          <KpiCard label="Margen" value="N/D" hint={motivoTexto(data.finanzas.margen_motivo)} />
        </div>
      </Panel>

      {pendientes.length > 0 ? (
        <details className="rounded-2xl border border-[var(--bf-border)] bg-white p-4">
          <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
            Indicadores no disponibles
          </summary>
          <p className="mt-1 text-xs text-[var(--bf-muted)]">
            El backend explica por qué no se puede calcular cada uno. No se muestran ceros en su lugar.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {pendientes.map(([clave, razon]) => (
              <li key={clave} className="flex flex-wrap justify-between gap-2">
                <span className="font-medium text-[var(--bf-ink)]">{ETIQUETAS_PENDIENTES[clave] ?? clave}</span>
                <span className="text-[var(--bf-muted)]">{motivoTexto(razon)}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <details className="rounded-2xl border border-[var(--bf-border)] bg-white p-4">
        <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
          Definiciones del cálculo
        </summary>
        <p className="mt-1 text-xs text-[var(--bf-muted)]">Zona horaria del backend: {data.definiciones.zona_horaria}.</p>
        <dl className="mt-3 space-y-2 text-xs text-[var(--bf-muted)]">
          <Definicion termino="Días de cultivo" texto={data.definiciones.dias_cultivo} />
          <Definicion termino="Semana de cultivo" texto={data.definiciones.semana_cultivo} />
          <Definicion termino="Unidad de masa" texto={data.definiciones.unidad_masa_productiva} />
          <Definicion termino="Población histórica" texto={data.definiciones.poblacion_as_of} />
          <Definicion termino="Serie de biomasa" texto={data.definiciones.serie_biomasa} />
          <Definicion termino="Serie de FCA acumulado" texto={data.definiciones.serie_fca} />
          <Definicion termino="Alimento convertible" texto={data.definiciones.alimento_convertible_kg} />
          <Definicion termino="Estadísticas" texto={data.definiciones.estadisticas} />
          <Definicion termino="Mediana" texto={data.definiciones.mediana} />
          <Definicion termino="Variación porcentual" texto={data.definiciones.variacion_porcentual} />
          <Definicion termino="Real vs objetivo" texto={data.definiciones.comparacion_real_objetivo} />
          <Definicion termino="Estado analítico" texto={data.definiciones.estado_analitico} />
          <Definicion termino="Cumplimiento de rango" texto={data.definiciones.cumplimiento_rango} />
          <Definicion termino="Recomendaciones" texto={data.definiciones.recomendaciones} />
          <Definicion termino="FCA acumulado" texto={data.definiciones.fca} />
          <Definicion termino="Ración recomendada" texto={data.definiciones.racion_diaria_recomendada_kg} />
          <Definicion termino="Filtros de fecha" texto={data.definiciones.filtros_fecha} />
        </dl>
      </details>
    </div>
  );
}

function SeccionProduccion({ data, modoOperativo = false }: { data: AnalisisLote; modoOperativo?: boolean }) {
  const est = data.estadisticas;

  const puntosPeso = useMemo(
    () =>
      data.biometrias.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        peso: toNumber(fila.peso_promedio_g),
        esperado: toNumber(fila.peso_esperado_g),
      })),
    [data.biometrias],
  );
  const hayEsperado = puntosPeso.some((punto) => punto.esperado !== null);
  const puntosTalla = useMemo(
    () =>
      data.biometrias
        .filter((fila) => fila.talla_promedio != null)
        .map((fila) => ({
          etiqueta: formatDateTime(fila.fecha_hora),
          talla: toNumber(fila.talla_promedio),
          unidad: fila.unidad_talla,
        })),
    [data.biometrias],
  );
  const unidadesTalla = useMemo(
    () => new Set(puntosTalla.map((punto) => punto.unidad ?? "")),
    [puntosTalla],
  );
  const puntosCrecimiento = useMemo(
    () =>
      data.serie_crecimiento.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        ganancia: toNumber(fila.ganancia_peso_g),
      })),
    [data.serie_crecimiento],
  );

  const puntosBiomasa = useMemo(
    () =>
      data.serie_biomasa.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        biomasa: toNumber(fila.biomasa_kg),
        ganancia: toNumber(fila.ganancia_biomasa_kg),
      })),
    [data.serie_biomasa],
  );
  const hayGanancia = puntosBiomasa.some((punto) => punto.ganancia !== null);

  const puntosPoblacion = useMemo(
    () =>
      data.serie_poblacion.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        poblacion: fila.poblacion_estimada,
        mortalidad: fila.mortalidad_acumulada,
        supervivencia: toNumber(fila.supervivencia_porcentaje),
      })),
    [data.serie_poblacion],
  );

  const puntosMortalidad = useMemo(
    () =>
      data.mortalidades.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        cantidad: fila.cantidad,
        acumulada: fila.acumulada,
        porcentaje: toNumber(fila.mortalidad_porcentaje),
      })),
    [data.mortalidades],
  );

  const puntosFca = useMemo(
    () =>
      data.serie_fca.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        fca: toNumber(fila.fca),
      })),
    [data.serie_fca],
  );
  const fcaSinDato = data.serie_fca.filter((fila) => !fila.fca_disponible);
  const evalPeso = buscarEvaluacion(data.evaluaciones, "peso_promedio_g");
  const colorRealPeso = colorSerieRealEvaluacion(evalPeso);
  const puntosComparativosPeso = useMemo(
    (): PuntoComparativo[] =>
      puntosPeso.map((punto) => ({
        etiqueta: punto.etiqueta,
        real: punto.peso,
        esperado: punto.esperado,
        minimo: null,
        maximo: null,
        objetivo: null,
      })),
    [puntosPeso],
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Indicador
          label="Ganancia de peso (g)"
          valor={data.indicadores.ganancia_peso_g}
          digitos={3}
          motivo={data.pendientes.ganancia_peso_g}
        />
        <Indicador
          label="Ganancia diaria (g/día)"
          valor={data.indicadores.ganancia_diaria_g}
          digitos={4}
          motivo={data.pendientes.ganancia_diaria_g}
        />
        <Indicador
          label="SGR (%/día)"
          valor={data.indicadores.sgr_pct_dia}
          digitos={2}
          motivo={data.pendientes.sgr_pct_dia}
        />
        <Indicador
          label="Desviación de peso (%)"
          valor={data.eficiencia.desviacion_peso_porcentaje}
          digitos={2}
          motivo={data.eficiencia.desviacion_peso_porcentaje === null ? "SIN_REFERENCIA_PRODUCCION_APLICABLE" : undefined}
        />
        <Indicador
          label="Ganancia de biomasa (kg)"
          valor={data.productividad.ganancia_biomasa_kg}
          digitos={2}
          motivo={data.productividad.motivos.ganancia_biomasa_kg}
        />
        <Indicador label="Peso cosechado (kg)" valor={data.productividad.peso_cosechado_kg} digitos={3} />
        <Indicador
          label={data.indicadores.unidad_talla ? `Talla promedio (${data.indicadores.unidad_talla})` : "Talla promedio"}
          valor={data.indicadores.talla_promedio}
          digitos={2}
          motivo={data.indicadores.talla_promedio === null ? "SIN_TALLA" : undefined}
        />
        <Indicador
          label="Densidad (kg/m³)"
          valor={data.indicadores.densidad_kg_m3}
          digitos={2}
          motivo={data.pendientes.densidad_kg_m3}
        />
      </div>

      <ChartCard
        title="Peso real vs peso esperado"
        unidad="g"
        descripcion={
          hayEsperado
            ? "Peso real de cada biometría contra el peso esperado de la referencia de esa misma semana de cultivo."
            : "Peso real de cada biometría. Ninguna semana con biometría tiene referencia aplicable, así que no se dibuja el esperado."
        }
        stats={est.peso_promedio_g}
        vacio={puntosPeso.length === 0}
        vacioMensaje="Sin biometrías en el rango: no hay curva de peso."
      >
        <ComparativeLineChart
          data={puntosComparativosPeso}
          unidad="g"
          colorReal={colorRealPeso}
          digitos={2}
          mostrarBandaRango={false}
        />
      </ChartCard>

      {modoOperativo ? (
        <>
          <p className="text-xs text-[var(--bf-muted)]" title={FCA_HINT_ECONOMICO}>
            {FCA_LABEL}: {FCA_DEFINICION} No hay FCA esperado oficial.
          </p>
          <ComparacionAlimentacion data={data} />
        </>
      ) : null}

      {!modoOperativo ? (
      <>
      <ChartCard
        title="Talla promedio vs tiempo"
        unidad={est.talla_promedio.unidad}
        descripcion={
          unidadesTalla.size > 1
            ? "Hay tallas con unidades distintas. No se mezclan en una sola gráfica ni se convierten."
            : "Talla tal como se registró en cada biometría. No hay conversión de unidades."
        }
        stats={unidadesTalla.size > 1 ? undefined : est.talla_promedio}
        vacio={puntosTalla.length === 0 || unidadesTalla.size > 1}
        vacioMensaje={
          puntosTalla.length === 0
            ? "N/D — no existen mediciones de talla registradas."
            : "Sin datos suficientes para graficar: unidades de talla distintas."
        }
      >
        <TimeSeriesChart
          data={puntosTalla}
          series={[{ key: "talla", nombre: "Talla promedio" }]}
          unidad={est.talla_promedio.unidad}
          digitos={2}
        />
      </ChartCard>

      <ChartCard
        title="Crecimiento vs tiempo"
        unidad="g"
        descripcion="Ganancia de peso individual respecto al peso inicial del lote en cada biometría."
        vacio={puntosCrecimiento.filter((punto) => punto.ganancia !== null).length === 0}
        vacioMensaje="Sin peso inicial o biometrías suficientes para calcular crecimiento."
      >
        <TimeSeriesChart
          data={puntosCrecimiento}
          series={[{ key: "ganancia", nombre: "Ganancia de peso (g)" }]}
          unidad="g"
        />
      </ChartCard>

      <ChartCard
        title="Biomasa vs tiempo"
        unidad="kg"
        descripcion="Cada punto usa la población reconstruida a esa fecha, no la población actual."
        stats={est.biomasa_kg}
        vacio={puntosBiomasa.length === 0}
        vacioMensaje={`Serie histórica de biomasa no disponible. Biomasa actual: ${
          data.indicadores.biomasa_actual_kg == null
            ? `N/D (${data.pendientes.biomasa_actual_kg ?? "SIN_BIOMETRIA"})`
            : `${formatNumber(data.indicadores.biomasa_actual_kg, { maximumFractionDigits: 3 })} kg`
        }.`}
      >
        <TimeSeriesChart
          data={puntosBiomasa}
          series={
            hayGanancia
              ? [
                  { key: "biomasa", nombre: "Biomasa (kg)" },
                  { key: "ganancia", nombre: "Ganancia sobre la siembra (kg)", color: "#1c4f43" },
                ]
              : [{ key: "biomasa", nombre: "Biomasa (kg)" }]
          }
          unidad="kg"
        />
      </ChartCard>

      <ChartCard
        title="Población estimada y mortalidad acumulada"
        unidad="peces"
        descripcion="Series históricas del backend. No se reconstruye población en el cliente."
        stats={est.poblacion_estimada}
        digitos={0}
        vacio={puntosPoblacion.length === 0}
        vacioMensaje="El backend no entrega serie histórica de población para este rango."
      >
        <TimeSeriesChart
          data={puntosPoblacion}
          series={[
            { key: "poblacion", nombre: "Población estimada" },
            { key: "mortalidad", nombre: "Mortalidad acumulada", color: "#b45309" },
          ]}
          unidad="peces"
          digitos={0}
        />
      </ChartCard>

      <ChartCard
        title="Supervivencia vs tiempo"
        unidad="%"
        descripcion="Población de cada fecha sobre la cantidad sembrada. Si solo hay un punto, el KPI de supervivencia está en Resumen."
        stats={est.supervivencia_porcentaje}
        digitos={2}
        vacio={puntosPoblacion.filter((punto) => punto.supervivencia !== null).length === 0}
        vacioMensaje="Sin serie de supervivencia. Supervivencia actual se muestra como KPI, no se inventa una curva."
      >
        <TimeSeriesChart
          data={puntosPoblacion}
          series={[{ key: "supervivencia", nombre: "Supervivencia (%)" }]}
          unidad="%"
          digitos={2}
        />
      </ChartCard>

      <ChartCard
        title="Mortalidad registrada y acumulada"
        unidad="peces"
        descripcion="Barras: mortalidad de cada fecha. Línea: acumulado que entrega el backend."
        stats={est.mortalidad_acumulada}
        digitos={0}
        vacio={puntosMortalidad.length === 0}
        vacioMensaje="Sin mortalidades en el rango."
      >
        <CategoryBarChart
          data={puntosMortalidad}
          barras={[{ key: "cantidad", nombre: "Mortalidad de la fecha" }]}
          lineas={[{ key: "acumulada", nombre: "Acumulada" }]}
          unidad="peces"
          digitos={0}
        />
      </ChartCard>

      <ChartCard
        title={FCA_SERIE_TITULO}
        descripcion={FCA_SERIE_DESCRIPCION}
        stats={est.fca}
        digitos={4}
        vacio={puntosFca.filter((punto) => punto.fca !== null).length === 0}
        vacioMensaje={
          fcaSinDato.length > 0
            ? `FCA acumulado no disponible en el rango: ${motivoTexto(fcaSinDato[fcaSinDato.length - 1].fca_motivo)}`
            : "Sin puntos con FCA acumulado calculable."
        }
      >
        <TimeSeriesChart
          data={puntosFca.filter((punto) => punto.fca !== null)}
          series={[{ key: "fca", nombre: FCA_LABEL }]}
          digitos={4}
        />
      </ChartCard>
      </>
      ) : null}

      {!modoOperativo && fcaSinDato.length > 0 ? (
        <Panel
          title="Puntos sin FCA acumulado"
          hint="El backend indica por qué cada punto no es calculable. No se sustituye por el FCA acumulado final. No es un FCA de intervalo."
        >
          <DataTable
            rows={fcaSinDato}
            rowKey={(row) => row.biometria_id}
            columns={[
              { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
              {
                key: "alimento",
                header: "Alimento acumulado (kg)",
                render: (row) =>
                  row.alimento_real_acumulado_kg == null
                    ? "N/D"
                    : formatNumber(row.alimento_real_acumulado_kg, { maximumFractionDigits: 3 }),
              },
              {
                key: "ganancia",
                header: "Ganancia de biomasa (kg)",
                render: (row) =>
                  row.ganancia_biomasa_kg == null
                    ? "N/D"
                    : formatNumber(row.ganancia_biomasa_kg, { maximumFractionDigits: 3 }),
              },
              { key: "motivo", header: "Motivo", render: (row) => motivoTexto(row.fca_motivo) ?? "—" },
            ]}
          />
        </Panel>
      ) : null}
    </div>
  );
}

function SeccionAgua({ data, modoOperativo = false }: { data: AnalisisLote; modoOperativo?: boolean }) {
  const grupos = useMemo(() => agruparAguaPorParametro(data.agua_serie), [data.agua_serie]);
  const statsPorParametro = useMemo(() => {
    const mapa = new Map<number, AnalisisStats>();
    const meta = new Map<number, { fuera: number | null; pct: string | number | null; conRef: boolean }>();
    for (const fila of data.estadisticas.agua) {
      mapa.set(fila.parametro_id, fila.estadisticas);
      meta.set(fila.parametro_id, {
        fuera: fila.fuera_de_rango_n,
        pct: fila.fuera_de_rango_porcentaje,
        conRef: fila.con_referencia,
      });
    }
    return { mapa, meta };
  }, [data.estadisticas.agua]);
  const tarjetasAgua = data.evaluaciones.filter((ev) => /^agua:\d+$/.test(ev.indicador));
  const historial = [...data.agua_serie].reverse();

  return (
    <div className="space-y-4">
      {tarjetasAgua.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {tarjetasAgua.map((ev) => (
            <RealReferenceCard key={ev.indicador} evaluacion={ev} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--bf-muted)]">N/D — Sin medición.</p>
      )}

      <Panel
        title="Historial de mediciones de agua"
        hint="Solo este lote. Más reciente primero. El rango es el de referencias_agua para la especie y etapa del lote."
      >
        <DataTable
          rows={historial}
          rowKey={(row) => row.id}
          empty="Sin mediciones de agua."
          maxVisibleRows={10}
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "parametro", header: "Parámetro" },
            {
              key: "valor",
              header: "Valor",
              render: (row) => `${formatNumber(row.valor, { maximumFractionDigits: 4 })} ${row.unidad}`,
            },
            { key: "unidad", header: "Unidad", render: (row) => row.unidad },
            {
              key: "estado",
              header: "Estado",
              render: (row) =>
                row.fuera_de_rango == null ? (
                  <StatusBadge label="N/D — Sin referencia configurada" tone="neutral" />
                ) : row.fuera_de_rango ? (
                  <StatusBadge label={etiquetaCumplimiento("FUERA_RANGO")} tone="danger" />
                ) : (
                  <StatusBadge label={etiquetaCumplimiento("DENTRO_RANGO")} tone="ok" />
                ),
            },
            {
              key: "usuario",
              header: "Usuario",
              render: (row) => row.registrado_por_nombre || (row.registrado_por != null ? `#${row.registrado_por}` : "—"),
            },
          ]}
        />
      </Panel>

      {grupos.length === 0 ? (
        modoOperativo ? (
          <p className="text-sm text-[var(--bf-muted)]">Sin mediciones de agua en el ciclo.</p>
        ) : (
        <ChartCard title="Parámetros de agua" vacio vacioMensaje="Sin mediciones de agua en el rango.">
          <span />
        </ChartCard>
        )
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {grupos
            .filter((grupo) => grupo.puntos.length >= 1)
            .map((grupo) => {
            const stats = statsPorParametro.mapa.get(grupo.parametro_id) ?? null;
            const meta = statsPorParametro.meta.get(grupo.parametro_id);
            const evalParam = buscarEvaluacion(data.evaluaciones, `agua:${grupo.parametro_id}`);
            const ref = {
              minimo: grupo.valorMinimo ?? toNumber(evalParam?.minimo),
              maximo: grupo.valorMaximo ?? toNumber(evalParam?.maximo),
              objetivo: toNumber(evalParam?.objetivo),
            };
            const puntosComparativos = prepararPuntosComparativos(grupo.puntos, ref);
            const evalBadge =
              evalParam && evalParam.cumplimiento_rango !== "NO_EVALUABLE" ? (
                <StatusBadge
                  label={etiquetaCumplimiento(evalParam.cumplimiento_rango)}
                  tone={toneCumplimiento(evalParam.cumplimiento_rango)}
                />
              ) : null;
            return (
              <ChartCard
                key={grupo.parametro_id}
                title={`${grupo.parametro} real vs referencia`}
                unidad={grupo.unidad}
                descripcion={
                  meta?.conRef && meta.fuera !== null
                    ? `Fuera de rango: ${meta.fuera} de ${stats?.n ?? "N/D"} mediciones${
                        meta.pct == null
                          ? "."
                          : ` (${formatNumber(meta.pct, { maximumFractionDigits: 2 })} %).`
                      }`
                    : meta?.conRef
                      ? "Comparación de mediciones contra el rango de referencia configurado."
                      : "N/D — Sin referencia configurada para esta especie y etapa."
                }
                stats={modoOperativo ? undefined : stats}
                digitos={4}
              >
                {evalBadge ? <div className="mb-2">{evalBadge}</div> : null}
                <ComparativeLineChart
                  data={puntosComparativos}
                  unidad={grupo.unidad}
                  colorReal={colorSerieRealEvaluacion(evalParam)}
                  digitos={4}
                />
              </ChartCard>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SeccionBiofloc({ data, modoOperativo = false }: { data: AnalisisLote; modoOperativo?: boolean }) {
  const serie = useMemo(() => prepararBiofloc(data.biofloc_serie), [data.biofloc_serie]);
  const est = data.estadisticas;
  const ultima = data.biofloc;
  const evalVolumen = buscarEvaluacion(data.evaluaciones, "volumen_sedimentable");
  const unidadVolumen = evalVolumen?.unidad || ultima?.unidad || est.volumen_sedimentable.unidad;
  const puntosComparativos = useMemo(
    () => prepararPuntosComparativos(serie.puntosVolumen, referenciaDesdeEvaluacion(evalVolumen)),
    [serie.puntosVolumen, evalVolumen],
  );
  const historialBiofloc = [...data.biofloc_serie].reverse();

  const descripcionVolumen = evalVolumen
    ? evalVolumen.explicacion
    : ultima
      ? "N/D — Sin referencia configurada para esta especie y etapa."
      : "N/D — Sin medición de sólidos sedimentables en el rango.";

  return (
    <div className="space-y-4">
      {evalVolumen ? <RealReferenceCard evaluacion={evalVolumen} /> : null}

      {(!modoOperativo || serie.puntosVolumen.length >= 1) ? (
      <ChartCard
        title="Sólidos sedimentables real vs referencia"
        unidad={unidadVolumen}
        descripcion={descripcionVolumen}
        stats={modoOperativo ? undefined : est.volumen_sedimentable}
        digitos={2}
        vacio={serie.puntosVolumen.length === 0}
        vacioMensaje={ultima ? "Sin puntos en el rango seleccionado." : "N/D — Sin medición"}
      >
        <ComparativeLineChart
          data={puntosComparativos}
          unidad={unidadVolumen}
          colorReal={colorSerieRealEvaluacion(evalVolumen)}
          digitos={2}
        />
      </ChartCard>
      ) : null}

      <Panel
        title="Historial de mediciones Biofloc"
        hint="Mediciones de sólidos sedimentables de este lote. No incluye aplicaciones."
      >
        <DataTable
          rows={historialBiofloc}
          rowKey={(row) => row.id}
          empty="N/D — Sin medición."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "parametro", header: "Parámetro", render: () => "Sólidos sedimentables" },
            {
              key: "valor",
              header: "Valor",
              render: (row) =>
                `${formatNumber(row.volumen_sedimentable, { maximumFractionDigits: 2 })} ${row.unidad}`,
            },
            { key: "unidad", header: "Unidad", render: (row) => row.unidad },
            {
              key: "estado",
              header: "Estado",
              render: (row) => {
                const valor = toNumber(row.volumen_sedimentable);
                const estado = cumplimientoPorRango(
                  valor,
                  toNumber(evalVolumen?.minimo),
                  toNumber(evalVolumen?.maximo),
                );
                if (estado === "NO_EVALUABLE") {
                  return <StatusBadge label="N/D — Sin referencia configurada" tone="neutral" />;
                }
                return (
                  <StatusBadge
                    label={etiquetaCumplimiento(estado)}
                    tone={toneCumplimiento(estado)}
                  />
                );
              },
            },
            {
              key: "usuario",
              header: "Usuario",
              render: (row) => row.registrado_por_nombre || (row.registrado_por != null ? `#${row.registrado_por}` : "—"),
            },
          ]}
        />
      </Panel>

      {!modoOperativo ? (
      <Panel title="Última medición de biofloc">
        {ultima ? (
          <dl className="space-y-2 text-sm">
            <Fila
              termino="Volumen sedimentable"
              valor={`${formatNumber(ultima.volumen_sedimentable, { maximumFractionDigits: 2 })} ${ultima.unidad}`}
            />
            {evalVolumen ? (
              <>
                {evalVolumen.objetivo !== null ? (
                  <Fila
                    termino="Objetivo"
                    valor={`${formatNumber(evalVolumen.objetivo, { maximumFractionDigits: 2 })} ${evalVolumen.unidad ?? ultima.unidad}`}
                  />
                ) : null}
                {evalVolumen.minimo !== null || evalVolumen.maximo !== null ? (
                  <Fila
                    termino="Rango"
                    valor={`${evalVolumen.minimo == null ? "—" : formatNumber(evalVolumen.minimo, { maximumFractionDigits: 2 })} – ${
                      evalVolumen.maximo == null ? "—" : formatNumber(evalVolumen.maximo, { maximumFractionDigits: 2 })
                    } ${evalVolumen.unidad ?? ultima.unidad}`}
                  />
                ) : null}
                {evalVolumen.cumplimiento_rango !== "NO_EVALUABLE" ? (
                  <Fila
                    termino="Estado"
                    valor={
                      <StatusBadge
                        label={etiquetaCumplimiento(evalVolumen.cumplimiento_rango)}
                        tone={toneCumplimiento(evalVolumen.cumplimiento_rango)}
                      />
                    }
                  />
                ) : null}
              </>
            ) : (
              <Fila termino="Referencia" valor="N/D — Sin referencia configurada" />
            )}
            <Fila termino="Fecha" valor={formatDateTime(ultima.fecha_hora)} />
          </dl>
        ) : (
          <p className="text-sm text-[var(--bf-muted)]">N/D — Sin medición</p>
        )}
      </Panel>
      ) : null}
    </div>
  );
}

/** Alimentación real vs recomendada — solo comparación, sin gráficas históricas de acumulado. */
function puntosAlimentacionComparativa(data: AnalisisLote): PuntoComparativo[] {
  const serie = data.serie_alimentacion_comparativa ?? [];
  return serie.map((punto) => ({
    etiqueta: formatDate(punto.fecha),
    real: toNumber(punto.real_kg),
    recomendado: toNumber(punto.recomendada_kg),
    minimo: null,
    maximo: null,
    objetivo: null,
  }));
}

function ReferenciaAlimentacionSemana({ ref }: { ref: ReferenciaAlimentacionActiva }) {
  const pesoUtilizado = etiquetaPesoUtilizado(ref.peso_utilizado);
  return (
    <Panel
      title="Referencia de producción y alimentación (semana actual)"
      hint={`Semana ${ref.semana_productiva}${ref.fase ? ` · Fase: ${ref.fase}` : ""}. La tasa y las raciones vienen de la referencia; la ración usa población viva y peso operativo.`}
    >
      <CamposAlimentacionRecomendada ref={ref} />
      {pesoUtilizado ? <p className="mt-3 text-xs text-[var(--bf-muted)]">{pesoUtilizado}.</p> : null}
    </Panel>
  );
}

function FilaDato({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{termino}</dt>
      <dd className="mt-0.5 font-medium text-[var(--bf-ink)]">{valor}</dd>
    </div>
  );
}

function ComparacionAlimentacion({ data }: { data: AnalisisLote }) {
  const ind = data.indicadores;
  const puntosRealVsRecomendado = useMemo(() => puntosAlimentacionComparativa(data), [data]);
  const evalAlimentacion = buscarEvaluacion(data.evaluaciones, "alimentacion_diaria_kg");
  const colorReal = colorSerieRealEvaluacion(evalAlimentacion);
  const ultimoPunto = (data.serie_alimentacion_comparativa ?? []).at(-1);
  const ultimaAlimentacion = data.alimentacion_real.length
    ? data.alimentacion_real[data.alimentacion_real.length - 1]
    : null;

  return (
    <div className="space-y-4">
      {data.referencia_alimentacion ? <ReferenciaVsLoteReal data={data} Panel={Panel} /> : null}
      {data.referencia_alimentacion ? (
        <ReferenciaAlimentacionSemana ref={data.referencia_alimentacion} />
      ) : (
        <Panel title="Referencia de producción y alimentación (semana actual)">
          <p className="text-sm text-[var(--bf-muted)]">N/D — Sin referencia configurada.</p>
        </Panel>
      )}

      {puntosRealVsRecomendado.length >= 2 ? (
        <ChartCard
          title="Alimentación real vs recomendada"
          unidad="kg"
          descripcion="Suma diaria real frente a la ración recomendada recalculada por semana, población y peso."
          vacio={puntosRealVsRecomendado.length === 0}
          vacioMensaje="Sin alimentaciones convertibles a kg."
        >
          <ComparativeLineChart
            data={puntosRealVsRecomendado}
            unidad="kg"
            colorReal={colorReal}
            digitos={3}
            mostrarBandaRango={false}
          />
        </ChartCard>
      ) : (
        <Panel title="Alimentación real vs recomendada" hint="Comparación puntual: menos de dos días con alimentación.">
          <dl className="grid gap-4 sm:grid-cols-2 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">REAL</dt>
              <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
                {ultimaAlimentacion
                  ? `${formatNumber(ultimaAlimentacion.cantidad, { maximumFractionDigits: 3 })} ${ultimaAlimentacion.unidad}`
                  : "N/D — Sin medición"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">RECOMENDADA</dt>
              <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
                {ind.racion_diaria_recomendada_kg == null
                  ? "N/D"
                  : `${formatNumber(ind.racion_diaria_recomendada_kg, { maximumFractionDigits: 3 })} kg`}
              </dd>
            </div>
          </dl>
        </Panel>
      )}

      {ultimoPunto && ultimoPunto.recomendada_kg != null ? (
        <Panel title="Desviación del último día registrado">
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <FilaDato
              termino="Real"
              valor={`${formatNumber(ultimoPunto.real_kg, { maximumFractionDigits: 3 })} kg`}
            />
            <FilaDato
              termino="Recomendada"
              valor={`${formatNumber(ultimoPunto.recomendada_kg, { maximumFractionDigits: 3 })} kg`}
            />
            <FilaDato
              termino="Desviación"
              valor={
                ultimoPunto.desviacion_kg != null
                  ? `${formatNumber(ultimoPunto.desviacion_kg, { maximumFractionDigits: 3 })} kg`
                  : "N/D"
              }
            />
            <FilaDato
              termino="Desviación %"
              valor={
                ultimoPunto.desviacion_porcentaje != null
                  ? `${formatNumber(ultimoPunto.desviacion_porcentaje, { maximumFractionDigits: 2 })} %`
                  : "N/D"
              }
            />
          </dl>
        </Panel>
      ) : null}

      {evalAlimentacion ? <RealReferenceCard evaluacion={evalAlimentacion} /> : null}
    </div>
  );
}

function SeccionAlimentacion({ data, modoOperativo = false }: { data: AnalisisLote; modoOperativo?: boolean }) {
  const ind = data.indicadores;

  const puntosAcumulado = useMemo(
    () =>
      data.alimentacion_real.map((fila) => ({
        etiqueta: formatDateTime(fila.fecha_hora),
        acumulado: toNumber(fila.acumulado_kg),
      })),
    [data.alimentacion_real],
  );
  const diasKg = useMemo(() => totalizarAlimentoKgPorDia(data.alimentacion_real), [data.alimentacion_real]);
  const puntosRealVsRecomendado = useMemo(() => puntosAlimentacionComparativa(data), [data]);
  const evalAlimentacion = buscarEvaluacion(data.evaluaciones, "alimentacion_diaria_kg");
  const colorRealAlim = colorSerieRealEvaluacion(evalAlimentacion);
  const noConvertibles = useMemo(
    () => [...new Set(data.alimentacion_real.filter((fila) => !fila.convertible_a_kg).map((fila) => fila.unidad))],
    [data.alimentacion_real],
  );
  const ultimaAlimentacion = data.alimentacion_real.length
    ? data.alimentacion_real[data.alimentacion_real.length - 1]
    : null;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Indicador
          label="Alimento real acumulado (kg)"
          valor={ind.alimento_real_acumulado_kg}
          digitos={3}
          motivo={data.pendientes.alimento_real_acumulado_kg}
        />
        <Indicador
          label="Biomasa productiva (kg)"
          valor={data.eficiencia.ganancia_biomasa_kg}
          digitos={3}
          motivo={data.eficiencia.ganancia_biomasa_kg == null ? data.productividad.motivos.ganancia_biomasa_kg : undefined}
        />
        <Indicador label="Costo por kg" valor={data.eficiencia.costo_por_kg} motivo={data.eficiencia.costo_por_kg_motivo} />
        <Indicador
          label="Costo de alimentación"
          valor={data.eficiencia.costo_alimentacion}
          motivo={data.eficiencia.costo_alimentacion_motivo}
        />
      </div>

      {modoOperativo ? (
        <>
          {data.referencia_alimentacion ? <ReferenciaVsLoteReal data={data} Panel={Panel} /> : null}
          {data.referencia_alimentacion ? (
            <ReferenciaAlimentacionSemana ref={data.referencia_alimentacion} />
          ) : (
            <Panel title="Referencia de producción y alimentación (semana actual)">
              <p className="text-sm text-[var(--bf-muted)]">N/D — Sin referencia configurada.</p>
            </Panel>
          )}
          {evalAlimentacion ? <RealReferenceCard evaluacion={evalAlimentacion} /> : null}
          {puntosRealVsRecomendado.length >= 2 ? (
            <ChartCard
              title="Alimentación real vs recomendada"
              unidad="kg"
              descripcion="Suma diaria real frente a la ración recomendada recalculada por semana, población y peso."
              vacio={puntosRealVsRecomendado.length === 0}
              vacioMensaje="Sin alimentaciones convertibles a kg en el rango."
            >
              <ComparativeLineChart
                data={puntosRealVsRecomendado}
                unidad="kg"
                colorReal={colorRealAlim}
                digitos={3}
                mostrarBandaRango={false}
              />
            </ChartCard>
          ) : (
            <Panel
              title="Alimentación real vs recomendada"
              hint="Comparación puntual: un solo día con alimentación registrada."
            >
              <dl className="grid gap-4 sm:grid-cols-2 text-sm">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">REAL</dt>
                  <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
                    {ultimaAlimentacion
                      ? `${formatNumber(ultimaAlimentacion.cantidad, { maximumFractionDigits: 3 })} ${ultimaAlimentacion.unidad}`
                      : "N/D — Sin medición"}
                  </dd>
                  <dd className="text-xs text-[var(--bf-muted)]">
                    {ultimaAlimentacion
                      ? `Fecha: ${formatDateTime(ultimaAlimentacion.fecha_hora)}`
                      : "Sin alimentación registrada"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">RECOMENDADO</dt>
                  <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
                    {ind.racion_diaria_recomendada_kg == null
                      ? "N/D"
                      : `${formatNumber(ind.racion_diaria_recomendada_kg, { maximumFractionDigits: 3 })} kg`}
                  </dd>
                  <dd className="text-xs text-[var(--bf-muted)]">
                    {ind.racion_diaria_recomendada_kg == null
                      ? motivoTexto(data.pendientes.racion_diaria_recomendada_kg) ?? "Sin referencia actual"
                      : `Referencia actual · semana ${ind.semana_productiva_alimentacion ?? ind.semana_cultivo}`}
                  </dd>
                </div>
              </dl>
            </Panel>
          )}
        </>
      ) : (
        <>
      <Panel
        title="Real vs recomendado (comparación actual)"
        hint="Último día de alimentación registrado contra la ración recomendada vigente. No se reconstruye una ración histórica."
      >
        <dl className="grid gap-4 sm:grid-cols-2 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">REAL</dt>
            <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
              {ultimaAlimentacion
                ? `${formatNumber(ultimaAlimentacion.cantidad, { maximumFractionDigits: 3 })} ${ultimaAlimentacion.unidad}`
                : "N/D"}
            </dd>
            <dd className="text-xs text-[var(--bf-muted)]">
              {ultimaAlimentacion
                ? `Fecha: ${formatDateTime(ultimaAlimentacion.fecha_hora)}`
                : "Sin alimentación registrada"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">RECOMENDADO</dt>
            <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">
              {ind.racion_diaria_recomendada_kg == null
                ? "N/D"
                : `${formatNumber(ind.racion_diaria_recomendada_kg, { maximumFractionDigits: 3 })} kg`}
            </dd>
            <dd className="text-xs text-[var(--bf-muted)]">
              {ind.racion_diaria_recomendada_kg == null
                ? motivoTexto(data.pendientes.racion_diaria_recomendada_kg) ?? "Sin referencia actual"
                : `Referencia actual · semana ${ind.semana_productiva_alimentacion ?? ind.semana_cultivo}`}
            </dd>
          </div>
        </dl>
      </Panel>
      <p className="text-xs text-[var(--bf-muted)]">
        La ración recomendada es el indicador vigente del lote, no una serie histórica. No se dibuja sobre
        alimentaciones pasadas.
      </p>

      <ChartCard
        title="Alimento real acumulado (kg)"
        unidad="kg"
        descripcion="Acumulado que entrega el backend. Solo suma unidades de masa: si aparece una unidad no convertible, el acumulado queda sin valor."
        stats={data.estadisticas.alimento_acumulado_kg}
        vacio={puntosAcumulado.filter((punto) => punto.acumulado !== null).length === 0}
        vacioMensaje={
          noConvertibles.length > 0
            ? `Hay alimento en ${noConvertibles.join(", ")}: el backend no lo convierte a kg y no acumula.`
            : "Sin alimentaciones en el rango."
        }
      >
        <TimeSeriesChart
          data={puntosAcumulado}
          series={[{ key: "acumulado", nombre: "Acumulado (kg)" }]}
          unidad="kg"
        />
      </ChartCard>

      <ChartCard
        title="Alimento real por día (kg)"
        unidad="kg"
        descripcion="Suma diaria de alimento real convertido a kg por el backend. No se proyecta la recomendación vigente sobre fechas históricas."
        vacio={diasKg.length === 0}
        vacioMensaje="Sin alimentaciones convertibles a kg en el rango."
      >
        <CategoryBarChart
          data={diasKg.map((punto) => ({ etiqueta: punto.etiqueta, cantidad: punto.cantidad }))}
          barras={[{ key: "cantidad", nombre: "Real (kg)" }]}
          unidad="kg"
          digitos={3}
        />
      </ChartCard>

      <Panel
        title="Total real por unidad"
        hint="Cada unidad se totaliza aparte. El backend solo convierte a kg desde unidades de masa; no se suman litros con kilogramos."
      >
        {data.alimentacion_real_por_unidad.length === 0 ? (
          <p className="text-sm text-[var(--bf-muted)]">Sin alimentaciones registradas.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {data.alimentacion_real_por_unidad.map((fila) => (
              <li key={fila.unidad} className="flex justify-between">
                <span>{fila.unidad}</span>
                <span>{formatNumber(fila.cantidad, { maximumFractionDigits: 3 })}</span>
              </li>
            ))}
          </ul>
        )}
        {noConvertibles.length > 0 ? (
          <p className="mt-2 text-xs text-[var(--bf-muted)]">
            Unidades no convertibles a kg en este lote: {noConvertibles.join(", ")}. No se asume densidad ni
            equivalencia.
          </p>
        ) : null}
      </Panel>

      <Panel title="Alimentaciones registradas" hint="Registros reales del lote, inmutables.">
        <DataTable
          rows={data.alimentacion_real}
          rowKey={(row) => row.id}
          empty="Sin alimentaciones registradas en el rango."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "producto",
              header: "Producto",
              render: (row) => `${row.producto_nombre} (${row.producto_codigo})`,
            },
            {
              key: "cantidad",
              header: "Cantidad",
              render: (row) => `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })} ${row.unidad}`,
            },
            {
              key: "kg",
              header: "En kg",
              render: (row) =>
                row.cantidad_kg == null
                  ? "No convertible"
                  : formatNumber(row.cantidad_kg, { maximumFractionDigits: 3 }),
            },
            {
              key: "acumulado",
              header: "Acumulado (kg)",
              render: (row) =>
                row.acumulado_kg == null
                  ? "N/D"
                  : formatNumber(row.acumulado_kg, { maximumFractionDigits: 3 }),
            },
          ]}
        />
      </Panel>
        </>
      )}
    </div>
  );
}

function SeccionReferencia({ data }: { data: AnalisisLote }) {
  const ind = data.indicadores;
  const referencia = data.referencia_produccion;

  return (
    <div className="space-y-4">
      <Panel
        title="Real vs objetivo vs rango"
        hint="El backend entrega valores, desviaciones, cumplimiento y explicación. Fuera de rango no equivale a ALERTA o CRÍTICO sin zonas de severidad aprobadas."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          {data.evaluaciones
            .filter((evaluacion) => evaluacion.indicador !== "fca")
            .map((evaluacion) => (
              <RealReferenceCard key={evaluacion.indicador} evaluacion={evaluacion} />
            ))}
        </div>
        <p className="mt-3 text-xs text-[var(--bf-muted)]">{FCA_ESPERADO_ND}</p>
      </Panel>

      {data.recomendaciones.length > 0 ? (
        <Panel
          title="Recomendaciones trazables"
          hint="Solo aparecen cuando existe una medición y una regla configurada incumplida. No crean alarmas del ERP."
        >
          <ul className="space-y-3">
            {data.recomendaciones.map((recomendacion) => (
              <li
                key={recomendacion.indicador}
                className="rounded-lg border border-[var(--bf-border)] p-3 text-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-[var(--bf-ink)]">
                    {tituloRecomendacion(recomendacion.indicador, data.evaluaciones, data.agua)}
                  </span>
                  <StatusBadge label={etiquetaCumplimiento(recomendacion.cumplimiento_rango)} tone={toneCumplimiento(recomendacion.cumplimiento_rango)} />
                </div>
                <p className="mt-2 text-xs text-[var(--bf-muted)]">
                  {recomendacion.motivo}
                </p>
                <p className="mt-2 text-sm text-[var(--bf-ink)]">
                  {recomendacion.recomendacion}
                </p>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Panel title="Referencia de producción" hint={data.definiciones.referencia_produccion}>
        {referencia ? (
          <dl className="space-y-2 text-sm">
            <Fila termino="Semanas que cubre" valor={etiquetaRangoSemanas(referencia.semana_desde, referencia.semana_hasta)} />
            <Fila termino="Semana actual del lote" valor={String(ind.semana_cultivo)} />
            <Fila
              termino="Peso esperado"
              valor={
                referencia.peso_esperado_g == null
                  ? "N/D"
                  : `${formatNumber(referencia.peso_esperado_g, { maximumFractionDigits: 2 })} g`
              }
            />
            <Fila
              termino="Tasa de alimentación"
              valor={
                referencia.tasa_alimentacion_pct == null
                  ? "N/D"
                  : `${formatNumber(referencia.tasa_alimentacion_pct, { maximumFractionDigits: 3 })} %`
              }
            />
          </dl>
        ) : (
          <p className="text-sm text-[var(--bf-muted)]">
            Sin referencia aplicable para la semana {ind.semana_cultivo}. N/D — Sin referencia configurada.
          </p>
        )}
      </Panel>

      <Panel
        title="Peso real vs esperado por semana"
        hint="Cada biometría se compara con la referencia de su propia semana de cultivo."
      >
        <DataTable
          rows={data.biometrias}
          rowKey={(row) => row.id}
          empty="Sin biometrías en el rango."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "semana", header: "Semana", render: (row) => String(row.semana_cultivo) },
            {
              key: "real",
              header: "Real (g)",
              render: (row) =>
                row.peso_promedio_g == null
                  ? "N/D"
                  : formatNumber(row.peso_promedio_g, { maximumFractionDigits: 3 }),
            },
            {
              key: "esperado",
              header: "Esperado (g)",
              render: (row) =>
                row.peso_esperado_g == null
                  ? "Sin referencia"
                  : formatNumber(row.peso_esperado_g, { maximumFractionDigits: 2 }),
            },
            {
              key: "diferencia",
              header: "Diferencia (g)",
              render: (row) =>
                row.diferencia_peso_g == null
                  ? "—"
                  : formatNumber(row.diferencia_peso_g, { maximumFractionDigits: 3 }),
            },
            {
              key: "pct",
              header: "Diferencia %",
              render: (row) =>
                row.diferencia_peso_pct == null
                  ? "—"
                  : `${formatNumber(row.diferencia_peso_pct, { maximumFractionDigits: 2 })} %`,
            },
          ]}
        />
      </Panel>

      <Panel
        title="Referencias resueltas por semana"
        hint="Semanas con biometría más la semana actual. Cada una resuelve su propia referencia."
      >
        <DataTable
          rows={data.referencias_por_semana}
          rowKey={(row) => row.semana_cultivo}
          empty="Sin semanas para resolver."
          columns={[
            { key: "semana", header: "Semana", render: (row) => String(row.semana_cultivo) },
            {
              key: "peso",
              header: "Peso esperado (g)",
              render: (row) =>
                row.peso_esperado_g == null
                  ? "N/D"
                  : formatNumber(row.peso_esperado_g, { maximumFractionDigits: 2 }),
            },
            {
              key: "tasa",
              header: "Tasa (%)",
              render: (row) =>
                row.tasa_alimentacion_pct == null
                  ? "N/D"
                  : formatNumber(row.tasa_alimentacion_pct, { maximumFractionDigits: 3 }),
            },
            { key: "motivo", header: "Estado", render: (row) => motivoTexto(row.motivo) ?? "Referencia aplicada" },
          ]}
        />
      </Panel>

    </div>
  );
}

const TITULOS_HISTORICOS_PROHIBIDOS = [
  "talla promedio vs tiempo",
  "crecimiento vs tiempo",
  "biomasa vs tiempo",
  "volumen sedimentable vs tiempo",
  "relación c:n vs tiempo",
  "población estimada y mortalidad acumulada",
  "supervivencia vs tiempo",
  "evolución del fca acumulado",
  "fca vs tiempo",
  "mortalidad registrada y acumulada",
  "alimento real acumulado",
  "alimento real por día",
  "peso promedio vs tiempo",
];

export type SeccionOperativa = "resumen" | "produccion" | "agua" | "biofloc";

function RecomendacionesOperativas({ data }: { data: AnalisisLote }) {
  if (data.recomendaciones.length === 0) return null;
  return (
    <section className="mt-6">
      <h2 className="mb-4 font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-accent)]">
        Recomendaciones
      </h2>
      <ul className="space-y-3">
        {data.recomendaciones.map((recomendacion) => (
          <li
            key={recomendacion.indicador}
            className="rounded-2xl border border-[var(--bf-border)] bg-white p-4 text-sm shadow-[0_1px_2px_rgba(16,40,33,0.04)]"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-[var(--bf-ink)]">
                {tituloRecomendacion(recomendacion.indicador, data.evaluaciones, data.agua)}
              </span>
              <StatusBadge
                label={etiquetaCumplimiento(recomendacion.cumplimiento_rango)}
                tone={toneCumplimiento(recomendacion.cumplimiento_rango)}
              />
            </div>
            <p className="mt-2 text-xs text-[var(--bf-muted)]">{recomendacion.motivo}</p>
            <p className="mt-2 text-[var(--bf-ink)]">{recomendacion.recomendacion}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Indicadores del lote en la ficha del estanque, separados por sección. */
export function VistaOperativaAnalisis({
  loteId,
  seccion = "resumen",
}: {
  loteId: number;
  seccion?: SeccionOperativa;
}) {
  const query = useQuery({
    queryKey: ["analisis-lote", loteId, "", ""],
    queryFn: () => getAnalisisLote(loteId),
    refetchOnMount: "always",
  });

  useEffect(() => {
    if (query.isError) {
      void query.refetch();
    }
    // Una sola recuperación al montar: si el API volvió tras un corte, no dejar el error pegado.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loteId]);

  if (query.isLoading) {
    return <LoadingState label="Cargando comparaciones del lote…" />;
  }
  if (query.isError) {
    return (
      <div className="space-y-3 px-6 py-6">
        <ErrorAlert message={apiErrorMessage(query.error)} />
        <button type="button" className="bf-btn-secondary" onClick={() => void query.refetch()}>
          Reintentar
        </button>
      </div>
    );
  }
  if (!query.data) {
    return null;
  }

  const data = query.data;
  const recsAgua = data.recomendaciones.filter((item) => item.indicador.startsWith("agua:"));
  const recsBiofloc = data.recomendaciones.filter(
    (item) =>
      item.indicador.startsWith("biofloc") ||
      item.indicador.includes("volumen") ||
      item.indicador.includes("cn"),
  );

  return (
    <div className="-mx-1">
      {seccion === "resumen" ? (
        <section className="px-6 py-6">
          <SeccionResumen data={data} />
        </section>
      ) : null}
      {seccion === "produccion" ? <ProduccionDashboard data={data} /> : null}
      {seccion === "agua" ? (
        <section className="px-6 py-6">
          <SeccionAgua data={data} modoOperativo />
          <RecomendacionesOperativas data={{ ...data, recomendaciones: recsAgua }} />
        </section>
      ) : null}
      {seccion === "biofloc" ? (
        <section className="px-6 py-6">
          <SeccionBiofloc data={data} modoOperativo />
          <RecomendacionesOperativas data={{ ...data, recomendaciones: recsBiofloc }} />
        </section>
      ) : null}
    </div>
  );
}

/** Verificación estática: la ficha operativa no debe renderizar títulos históricos prohibidos. */
export function tituloPermitidoEnFichaOperativa(titulo: string): boolean {
  const normalizado = titulo.trim().toLowerCase();
  return !TITULOS_HISTORICOS_PROHIBIDOS.some((prohibido) => normalizado.includes(prohibido));
}
