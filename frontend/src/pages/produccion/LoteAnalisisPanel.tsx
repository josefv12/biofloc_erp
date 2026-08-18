import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAnalisisLote } from "../../api/analisis";
import { RealReferenceCard } from "../../components/analisis/RealReferenceCard";
import { CategoryBarChart } from "../../components/charts/CategoryBarChart";
import { ChartCard } from "../../components/charts/ChartCard";
import { TimeSeriesChart, type LineaReferencia } from "../../components/charts/TimeSeriesChart";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDateTime, formatNumber } from "../../utils/format";
import {
  agruparAguaPorParametro,
  prepararBiofloc,
  toNumber,
  totalizarAlimentoKgPorDia,
} from "../../utils/series";
import type { AnalisisLote, AnalisisStats } from "../../types/analisis";

type SeccionId = "resumen" | "produccion" | "agua" | "biofloc" | "alimentacion" | "referencia";

const SECCIONES: { id: SeccionId; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "produccion", label: "Producción" },
  { id: "agua", label: "Agua" },
  { id: "biofloc", label: "Biofloc" },
  { id: "alimentacion", label: "Alimentación" },
  { id: "referencia", label: "Real vs referencia" },
];

/** Traducción de los códigos técnicos que envía el backend en `pendientes`. */
const MOTIVOS: Record<string, string> = {
  SIN_BIOMETRIA: "Sin biometría registrada.",
  SIN_PESO_INICIAL_LOTE: "El lote no registra peso inicial promedio.",
  DIAS_CULTIVO_CERO: "El lote se sembró hoy: todavía no hay días de cultivo.",
  SIN_ALIMENTO_REAL_REGISTRADO: "Sin alimentación registrada.",
  UNIDAD_ALIMENTO_INCOMPATIBLE:
    "Hay alimento en una unidad que no es de masa: no se puede totalizar en kg.",
  SIN_BIOMASA_INICIAL: "Sin biomasa inicial disponible.",
  SIN_BIOMASA_FINAL: "Sin biomasa final disponible.",
  GANANCIA_BIOMASA_NO_POSITIVA: "La biomasa no creció respecto a la siembra.",
  SIN_REFERENCIA_PRODUCCION_APLICABLE: "No hay referencia de producción para esta semana.",
  REFERENCIA_SIN_TASA_ALIMENTACION: "La referencia no define tasa de alimentación.",
  REFERENCIA_SIN_PESO_ESPERADO: "La referencia no define peso esperado.",
  SIN_CONFIGURACION_DE_RACIONES: "No existe todavía una configuración de raciones diarias.",
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
};

const ETIQUETAS_PENDIENTES: Record<string, string> = {
  biomasa_inicial_kg: "Biomasa inicial",
  biomasa_actual_kg: "Biomasa actual",
  ganancia_peso_g: "Ganancia de peso",
  ganancia_diaria_g: "Ganancia diaria",
  alimento_real_acumulado_kg: "Alimento real acumulado",
  fca: "FCA",
  racion_diaria_recomendada_kg: "Ración diaria recomendada",
  numero_raciones_diarias: "Raciones por día",
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
      value={`${formatNumber(numero, { maximumFractionDigits: digitos })}${sufijo ? ` ${sufijo}` : ""}`}
      hint={motivoTexto(motivo)}
    />
  );
}

function Panel({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
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

function Fila({ termino, valor }: { termino: string; valor: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[var(--bf-muted)]">{termino}</dt>
      <dd>{valor}</dd>
    </div>
  );
}

export function LoteAnalisisPanel({ loteId }: { loteId: number }) {
  const [seccion, setSeccion] = useState<SeccionId>("resumen");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const rango = { fechaDesde: desde || undefined, fechaHasta: hasta || undefined };
  const query = useQuery({
    queryKey: ["analisis-lote", loteId, desde, hasta],
    queryFn: () => getAnalisisLote(loteId, rango),
  });

  const data = query.data;

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--bf-muted)]">
        Los indicadores, las series históricas y las estadísticas las calcula el API. Este panel solo ordena,
        formatea y grafica: no recalcula biomasa, población, supervivencia, FCA, ganancia ni ración.
      </p>

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

      {query.isLoading ? <LoadingState label="Cargando análisis…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}

      {data ? (
        <>
          {seccion === "resumen" ? <SeccionResumen data={data} /> : null}
          {seccion === "produccion" ? <SeccionProduccion data={data} /> : null}
          {seccion === "agua" ? <SeccionAgua data={data} /> : null}
          {seccion === "biofloc" ? <SeccionBiofloc data={data} /> : null}
          {seccion === "alimentacion" ? <SeccionAlimentacion data={data} /> : null}
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
        <Indicador
          label="Peso promedio (g)"
          valor={ind.peso_promedio_g}
          digitos={3}
          motivo={ind.peso_promedio_g === null ? "SIN_BIOMETRIA" : undefined}
        />
        <KpiCard
          label="Días de cultivo"
          value={formatNumber(ind.dias_cultivo)}
          hint={ind.semana_cultivo === 0 ? "Día de la siembra" : `Semana ${ind.semana_cultivo}`}
        />
        <Indicador
          label="Biomasa inicial (kg)"
          valor={ind.biomasa_inicial_kg}
          digitos={3}
          motivo={data.pendientes.biomasa_inicial_kg}
        />
        <Indicador
          label="Biomasa actual (kg)"
          valor={ind.biomasa_actual_kg}
          digitos={3}
          motivo={data.pendientes.biomasa_actual_kg}
        />
        <Indicador
          label="Ganancia de peso (g)"
          valor={ind.ganancia_peso_g}
          digitos={3}
          motivo={data.pendientes.ganancia_peso_g}
        />
        <Indicador
          label="Ganancia diaria (g/día)"
          valor={ind.ganancia_diaria_g}
          digitos={4}
          motivo={data.pendientes.ganancia_diaria_g}
        />
        <Indicador label="FCA" valor={ind.fca} digitos={4} motivo={ind.fca_motivo} />
        <Indicador
          label="Alimento real acumulado (kg)"
          valor={ind.alimento_real_acumulado_kg}
          digitos={3}
          motivo={data.pendientes.alimento_real_acumulado_kg}
        />
        <Indicador
          label="Ración diaria recomendada (kg)"
          valor={ind.racion_diaria_recomendada_kg}
          digitos={3}
          motivo={data.pendientes.racion_diaria_recomendada_kg}
        />
        <Indicador
          label="Raciones por día"
          valor={ind.numero_raciones_diarias}
          digitos={0}
          motivo={data.pendientes.numero_raciones_diarias}
        />
      </div>

      <Panel title="Productividad" hint="Cuánto produce el lote. Todos los valores llegan calculados por el backend.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Indicador label="Biomasa actual (kg)" valor={data.productividad.biomasa_actual_kg} digitos={3} motivo={data.productividad.motivos.biomasa_actual_kg} />
          <Indicador label="Ganancia de biomasa (kg)" valor={data.productividad.ganancia_biomasa_kg} digitos={3} motivo={data.productividad.motivos.ganancia_biomasa_kg} />
          <Indicador label="Peso cosechado (kg)" valor={data.productividad.peso_cosechado_kg} digitos={3} />
          <KpiCard label="Peces cosechados" value={formatNumber(data.productividad.peces_cosechados)} />
          <Indicador label="Ganancia individual (g)" valor={data.productividad.ganancia_peso_g} digitos={3} />
          <Indicador label="Ganancia diaria (g/día)" valor={data.productividad.ganancia_diaria_g} digitos={4} />
          <Indicador label="Supervivencia (%)" valor={data.productividad.supervivencia_porcentaje} digitos={2} />
          <Indicador label="Mortalidad (%)" valor={data.productividad.mortalidad_porcentaje} digitos={2} />
        </div>
      </Panel>

      <Panel title="Eficiencia" hint="Qué recursos utiliza para producir. FCA usa exclusivamente alimento real convertible a kg.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Indicador label="FCA" valor={data.eficiencia.fca} digitos={4} motivo={data.eficiencia.fca_motivo} />
          <Indicador label="Alimento real (kg)" valor={data.eficiencia.alimento_real_acumulado_kg} digitos={3} />
          <Indicador label="Ganancia de biomasa (kg)" valor={data.eficiencia.ganancia_biomasa_kg} digitos={3} />
          <Indicador label="Desviación de peso (%)" valor={data.eficiencia.desviacion_peso_porcentaje} digitos={2} motivo={data.eficiencia.desviacion_peso_porcentaje === null ? "SIN_REFERENCIA_PRODUCCION_APLICABLE" : undefined} />
          <Indicador label="Costo por kg" valor={data.eficiencia.costo_por_kg} motivo={data.eficiencia.costo_por_kg_motivo} />
          <Indicador label="Costo de alimentación" valor={data.eficiencia.costo_alimentacion} motivo={data.eficiencia.costo_alimentacion_motivo} />
        </div>
      </Panel>

      <Panel title="Finanzas del lote" hint="Ingresos y gastos directamente vinculados al lote; no se prorratean costos de granja.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Ingresos vinculados" value={formatCop(data.finanzas.ingresos_lote)} hint={`${data.finanzas.ventas_registradas} venta(s)`} />
          <KpiCard label="Gastos imputados" value={formatCop(data.finanzas.gastos_directos_lote)} hint={`${data.finanzas.gastos_registrados} gasto(s)`} />
          <KpiCard label="Utilidad" value="N/D" hint={motivoTexto(data.finanzas.utilidad_motivo)} />
          <KpiCard label="Margen" value="N/D" hint={motivoTexto(data.finanzas.margen_motivo)} />
        </div>
      </Panel>

      {pendientes.length > 0 ? (
        <Panel
          title="Indicadores no disponibles"
          hint="El backend explica por qué no se puede calcular cada uno. No se muestran ceros en su lugar."
        >
          <ul className="space-y-2 text-sm">
            {pendientes.map(([clave, razon]) => (
              <li key={clave} className="flex flex-wrap justify-between gap-2">
                <span className="font-medium text-[var(--bf-ink)]">{ETIQUETAS_PENDIENTES[clave] ?? clave}</span>
                <span className="text-[var(--bf-muted)]">{motivoTexto(razon)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Panel title="Definiciones del cálculo" hint={`Zona horaria del backend: ${data.definiciones.zona_horaria}.`}>
        <dl className="space-y-2 text-xs text-[var(--bf-muted)]">
          <Definicion termino="Días de cultivo" texto={data.definiciones.dias_cultivo} />
          <Definicion termino="Semana de cultivo" texto={data.definiciones.semana_cultivo} />
          <Definicion termino="Unidad de masa" texto={data.definiciones.unidad_masa_productiva} />
          <Definicion termino="Población histórica" texto={data.definiciones.poblacion_as_of} />
          <Definicion termino="Serie de biomasa" texto={data.definiciones.serie_biomasa} />
          <Definicion termino="Serie de FCA" texto={data.definiciones.serie_fca} />
          <Definicion termino="Alimento convertible" texto={data.definiciones.alimento_convertible_kg} />
          <Definicion termino="Estadísticas" texto={data.definiciones.estadisticas} />
          <Definicion termino="Mediana" texto={data.definiciones.mediana} />
          <Definicion termino="Variación porcentual" texto={data.definiciones.variacion_porcentual} />
          <Definicion termino="Real vs objetivo" texto={data.definiciones.comparacion_real_objetivo} />
          <Definicion termino="Estado analítico" texto={data.definiciones.estado_analitico} />
          <Definicion termino="Cumplimiento de rango" texto={data.definiciones.cumplimiento_rango} />
          <Definicion termino="Recomendaciones" texto={data.definiciones.recomendaciones} />
          <Definicion termino="FCA" texto={data.definiciones.fca} />
          <Definicion termino="Ración recomendada" texto={data.definiciones.racion_diaria_recomendada_kg} />
          <Definicion termino="Filtros de fecha" texto={data.definiciones.filtros_fecha} />
        </dl>
      </Panel>
    </div>
  );
}

function SeccionProduccion({ data }: { data: AnalisisLote }) {
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

  return (
    <div className="space-y-4">
      <ChartCard
        title="Peso promedio vs peso esperado"
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
        <TimeSeriesChart
          data={puntosPeso}
          series={
            hayEsperado
              ? [
                  { key: "peso", nombre: "Peso real (g)" },
                  { key: "esperado", nombre: "Peso esperado (g)", color: "#b45309" },
                ]
              : [{ key: "peso", nombre: "Peso real (g)" }]
          }
          unidad="g"
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
        vacioMensaje="Sin biometrías en el rango: el backend no puede calcular biomasa por fecha."
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
        title="Población estimada vs tiempo"
        unidad="peces"
        descripcion="Un punto por evento productivo: siembra, mortalidad, cosecha y biometría."
        stats={est.poblacion_estimada}
        digitos={0}
        vacio={puntosPoblacion.length === 0}
        vacioMensaje="Sin eventos productivos en el rango."
      >
        <TimeSeriesChart
          data={puntosPoblacion}
          series={[{ key: "poblacion", nombre: "Población estimada" }]}
          unidad="peces"
          digitos={0}
        />
      </ChartCard>

      <ChartCard
        title="Supervivencia vs tiempo"
        unidad="%"
        descripcion="Población de cada fecha sobre la cantidad sembrada. No se repite el valor actual en fechas anteriores."
        stats={est.supervivencia_porcentaje}
        digitos={2}
        vacio={puntosPoblacion.length === 0}
        vacioMensaje="Sin eventos productivos en el rango."
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
        title="FCA vs tiempo"
        descripcion="Alimento real acumulado sobre ganancia de biomasa acumulada en cada biometría. Solo se dibujan los puntos donde el cálculo es válido."
        stats={est.fca}
        digitos={4}
        vacio={puntosFca.filter((punto) => punto.fca !== null).length === 0}
        vacioMensaje={
          fcaSinDato.length > 0
            ? `FCA no disponible en el rango: ${motivoTexto(fcaSinDato[fcaSinDato.length - 1].fca_motivo)}`
            : "Sin puntos con FCA calculable."
        }
      >
        <TimeSeriesChart
          data={puntosFca.filter((punto) => punto.fca !== null)}
          series={[{ key: "fca", nombre: "FCA" }]}
          digitos={4}
        />
      </ChartCard>

      {fcaSinDato.length > 0 ? (
        <Panel
          title="Puntos sin FCA"
          hint="El backend indica por qué cada punto no es calculable. No se sustituye por el FCA final."
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

function SeccionAgua({ data }: { data: AnalisisLote }) {
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

  return (
    <div className="space-y-4">
      <Panel
        title="Última medición por parámetro"
        hint="El rango proviene de referencias_agua para la especie y etapa del lote. Sin referencia no hay rango y el estado queda sin determinar."
      >
        <DataTable
          rows={data.agua}
          rowKey={(row) => row.parametro_id}
          empty="Sin mediciones de agua."
          columns={[
            { key: "parametro", header: "Parámetro" },
            {
              key: "valor",
              header: "Valor",
              render: (row) => `${formatNumber(row.valor, { maximumFractionDigits: 4 })} ${row.unidad}`,
            },
            {
              key: "rango",
              header: "Rango",
              render: (row) =>
                row.valor_minimo == null && row.valor_maximo == null
                  ? "Sin referencia"
                  : `${row.valor_minimo == null ? "—" : formatNumber(row.valor_minimo, { maximumFractionDigits: 4 })} – ${
                      row.valor_maximo == null ? "—" : formatNumber(row.valor_maximo, { maximumFractionDigits: 4 })
                    } ${row.unidad}`,
            },
            {
              key: "estado",
              header: "Estado",
              render: (row) =>
                row.fuera_de_rango == null ? (
                  <span className="text-[var(--bf-muted)]">Sin referencia</span>
                ) : row.fuera_de_rango ? (
                  <StatusBadge label="Fuera del rango" tone="danger" />
                ) : (
                  <StatusBadge label="Dentro del rango" tone="ok" />
                ),
            },
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
          ]}
        />
      </Panel>

      {grupos.length === 0 ? (
        <ChartCard title="Parámetros de agua" vacio vacioMensaje="Sin mediciones de agua en el rango.">
          <span />
        </ChartCard>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {grupos.map((grupo) => {
            const stats = statsPorParametro.mapa.get(grupo.parametro_id) ?? null;
            const meta = statsPorParametro.meta.get(grupo.parametro_id);
            const referencias: LineaReferencia[] = [];
            if (grupo.valorMinimo !== null) {
              referencias.push({
                valor: grupo.valorMinimo,
                etiqueta: `Mín ${formatNumber(grupo.valorMinimo, { maximumFractionDigits: 4 })}`,
              });
            }
            if (grupo.valorMaximo !== null) {
              referencias.push({
                valor: grupo.valorMaximo,
                etiqueta: `Máx ${formatNumber(grupo.valorMaximo, { maximumFractionDigits: 4 })}`,
              });
            }
            return (
              <ChartCard
                key={grupo.parametro_id}
                title={grupo.parametro}
                unidad={grupo.unidad}
                descripcion={
                  meta?.conRef && meta.fuera !== null
                    ? `Fuera de rango: ${meta.fuera} de ${stats?.n ?? "N/D"} mediciones${
                        meta.pct == null
                          ? "."
                          : ` (${formatNumber(meta.pct, { maximumFractionDigits: 2 })} %).`
                      }`
                    : "Sin referencia para esta especie y etapa: no se dibuja rango ni se evalúa el estado."
                }
                stats={stats}
                digitos={4}
              >
                <TimeSeriesChart
                  data={grupo.puntos}
                  series={[{ key: "valor", nombre: grupo.parametro }]}
                  unidad={grupo.unidad}
                  referencias={referencias}
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

function SeccionBiofloc({ data }: { data: AnalisisLote }) {
  const serie = useMemo(() => prepararBiofloc(data.biofloc_serie), [data.biofloc_serie]);
  const est = data.estadisticas;
  const ultima = data.biofloc;

  return (
    <div className="space-y-4">
      <ChartCard
        title="Volumen sedimentable vs tiempo"
        unidad={est.volumen_sedimentable.unidad}
        descripcion="Unidad tal como la entrega el API. No se define rango objetivo en esta fase."
        stats={est.volumen_sedimentable}
        digitos={2}
        vacio={serie.puntosVolumen.length === 0}
        vacioMensaje="Sin mediciones de biofloc en el rango."
      >
        <TimeSeriesChart
          data={serie.puntosVolumen}
          series={[{ key: "valor", nombre: "Volumen sedimentable" }]}
          unidad={est.volumen_sedimentable.unidad}
          digitos={2}
        />
      </ChartCard>

      <ChartCard
        title="Relación C:N vs tiempo"
        descripcion="Solo mediciones que registran relación C:N. No hay C:N objetivo, rango ni recomendación de carbono."
        stats={est.relacion_cn}
        digitos={3}
        vacio={serie.puntosCn.length === 0}
        vacioMensaje="Ninguna medición del rango registra relación C:N."
      >
        <TimeSeriesChart
          data={serie.puntosCn}
          series={[{ key: "valor", nombre: "Relación C:N" }]}
          digitos={3}
        />
      </ChartCard>

      <Panel title="Última medición de biofloc">
        {ultima ? (
          <dl className="space-y-2 text-sm">
            <Fila
              termino="Volumen sedimentable"
              valor={`${formatNumber(ultima.volumen_sedimentable, { maximumFractionDigits: 2 })} ${ultima.unidad}`}
            />
            <Fila
              termino="Relación C:N"
              valor={
                ultima.relacion_cn == null
                  ? "N/D"
                  : formatNumber(ultima.relacion_cn, { maximumFractionDigits: 3 })
              }
            />
            <Fila termino="Fecha" valor={formatDateTime(ultima.fecha_hora)} />
          </dl>
        ) : (
          <p className="text-sm text-[var(--bf-muted)]">Sin medición registrada.</p>
        )}
      </Panel>
    </div>
  );
}

function SeccionAlimentacion({ data }: { data: AnalisisLote }) {
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
  const noConvertibles = useMemo(
    () => [...new Set(data.alimentacion_real.filter((fila) => !fila.convertible_a_kg).map((fila) => fila.unidad))],
    [data.alimentacion_real],
  );

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
          label="Ración diaria recomendada (kg)"
          valor={ind.racion_diaria_recomendada_kg}
          digitos={3}
          motivo={data.pendientes.racion_diaria_recomendada_kg}
        />
        <Indicador label="FCA" valor={ind.fca} digitos={4} motivo={ind.fca_motivo} />
      </div>

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
              render: (row) => `${row.producto_codigo} — ${row.producto_nombre}`,
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
          {data.evaluaciones.map((evaluacion) => (
            <RealReferenceCard key={evaluacion.indicador} evaluacion={evaluacion} />
          ))}
        </div>
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
                    {recomendacion.indicador}
                  </span>
                  <StatusBadge label="Fuera del rango" tone="danger" />
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
            <Fila termino="Semanas que cubre" valor={`${referencia.semana_desde} – ${referencia.semana_hasta}`} />
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
            Sin referencia aplicable para la semana {ind.semana_cultivo}. No se asume ningún valor esperado.
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
