import { useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { getAnalisisLote, getComparativoEstanques } from "../../api/analisis";
import { KpiCard } from "../../components/KpiCard";
import {
  listMedicionesAgua,
  listParametrosAgua,
  listReferenciasAgua,
} from "../../api/operations";
import {
  createBiometria,
  createCosecha,
  createMortalidad,
  getEstanque,
  getLote,
  listBiometrias,
  listCosechas,
  listMortalidades,
} from "../../api/production";
import { LoteAnalisisPanel, VistaOperativaAnalisis, type SeccionOperativa } from "./LoteAnalisisPanel";
import { ChartCard } from "../../components/charts/ChartCard";
import { TimeSeriesChart } from "../../components/charts/TimeSeriesChart";
import { AguaMedicionesPanel } from "../operacion/AguaPage";
import { AplicacionesBioflocPanel, MedicionesBioflocPanel } from "../operacion/BioflocPage";
import { AlimentacionPanel } from "../operacion/AlimentacionPage";
import { PATH_COMPARACION, pathFichaEstanque } from "./fichaPaths";
import { apiErrorMessage } from "../../utils/apiError";
import {
  formatCop,
  formatDate,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
  withFechaHoraIso,
} from "../../utils/format";
import { mensajeRestantesCosecha } from "../../utils/indicadoresProduccion";
import {
  FCA_HINT_ECONOMICO,
  FCA_LABEL,
  fcaHintDisponible,
  fcaHintNoDisponible,
} from "../../utils/fcaPresentacion";
import { can } from "../../utils/rbac";
import { toNumber } from "../../utils/series";
import type { AnalisisLote } from "../../types/analisis";
import type { BiometriaCreate, CosechaCreate, Lote, MortalidadCreate } from "../../types/production";

type TabId =
  | "resumen"
  | "produccion"
  | "agua"
  | "biofloc"
  | "alimentacion"
  | "finanzas"
  | "historial";

const TABS: { id: TabId; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "produccion", label: "Producción" },
  { id: "agua", label: "Calidad de agua" },
  { id: "biofloc", label: "Biofloc" },
  { id: "alimentacion", label: "Alimentación" },
  { id: "finanzas", label: "Finanzas" },
  { id: "historial", label: "Historial" },
];

const TABS_OPERATIVOS: { id: TabId; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "produccion", label: "Producción" },
  { id: "agua", label: "Calidad de agua" },
  { id: "biofloc", label: "Biofloc" },
];
const TABS_OPERATIVOS_IDS = new Set(TABS_OPERATIVOS.map((item) => item.id));

const TAB_IDS = new Set<string>(TABS.map((item) => item.id));

/** URLs antiguas: las gráficas vivían en ?tab=analisis y el CRUD en pestañas sueltas. */
const TAB_ALIASES: Record<string, TabId> = {
  analisis: "produccion",
  biometrias: "produccion",
  mortalidades: "produccion",
  cosechas: "produccion",
};

export type LoteFichaTabId = TabId;

export function parseLoteFichaTab(valor: string | null, fallback: TabId = "resumen"): TabId {
  if (!valor) return fallback;
  if (TAB_IDS.has(valor)) return valor as TabId;
  if (valor in TAB_ALIASES) return TAB_ALIASES[valor];
  return fallback;
}

function invalidateAnalisis(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["analisis-lote"] }),
    queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] }),
    queryClient.invalidateQueries({ queryKey: ["analisis-estanque-historial"] }),
  ]);
}

export function LoteFichaPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const loteId = Number(id);
  const invalidId = !Number.isInteger(loteId) || loteId <= 0;
  const tab = parseLoteFichaTab(searchParams.get("tab"));

  // La pestaña vive en la URL para que la ficha sea compartible y el botón
  // atrás del navegador recorra las pestañas visitadas.
  function setTab(siguiente: TabId) {
    const params = new URLSearchParams(searchParams);
    params.set("tab", siguiente);
    params.delete("seccion");
    setSearchParams(params, { replace: false });
  }

  const loteQuery = useQuery({
    queryKey: ["lote", loteId],
    queryFn: () => getLote(loteId),
    enabled: !invalidId,
  });

  const estanqueQuery = useQuery({
    queryKey: ["estanque", loteQuery.data?.estanque_id],
    queryFn: () => getEstanque(loteQuery.data!.estanque_id),
    enabled: Boolean(loteQuery.data?.estanque_id),
  });

  if (invalidId) {
    return <ErrorAlert message="Identificador de lote inválido." />;
  }

  if (loteQuery.isLoading) {
    return <LoadingState label="Cargando ficha del lote…" />;
  }

  if (loteQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(loteQuery.error)} />
        <Link to="/produccion/lotes" className="bf-btn-secondary inline-flex">
          Volver a lotes
        </Link>
      </div>
    );
  }

  const lote = loteQuery.data;
  if (!lote) {
    return null;
  }

  const estanqueLabel = estanqueQuery.data
    ? `${estanqueQuery.data.codigo} · ${estanqueQuery.data.nombre}`
    : `#${lote.estanque_id}`;

  return (
    <div>
      <div className="rounded-2xl border border-[var(--bf-border)] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Lote</p>
            <h1 className="font-display text-3xl font-semibold text-[var(--bf-ink)]">{lote.codigo}</h1>
            <p className="mt-1 text-sm text-[var(--bf-muted)]">
              {lote.especie.nombre_comun} ·{" "}
              <Link
                to={pathFichaEstanque(lote.estanque_id, { loteId: lote.id })}
                className="text-[var(--bf-accent)] hover:underline"
              >
                Estanque {estanqueLabel}
              </Link>
            </p>
            <p className="mt-2 text-xs text-[var(--bf-muted)]">
              <Link to="/dashboard" className="hover:underline">
                Granja
              </Link>
              {" · "}
              <Link to={PATH_COMPARACION} className="hover:underline">
                Comparación
              </Link>
              {" · "}
              <Link to={pathFichaEstanque(lote.estanque_id, { loteId: lote.id })} className="hover:underline">
                Estanque
              </Link>
              {" · Lote"}
            </p>
          </div>
          <StatusBadge label={lote.estado.nombre} tone={lote.estado.nombre === "ACTIVO" ? "ok" : "neutral"} />
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-3">
          <Info label="Siembra" value={formatDate(lote.fecha_siembra)} />
          <Info label="Etapa" value={lote.etapa_productiva.nombre} />
          <Info
            label="Cantidad sembrada"
            value={formatNumber(lote.cantidad_sembrada)}
          />
        </dl>
      </div>

      <LoteFichaWorkspace lote={lote} tab={tab} onTab={setTab} />
    </div>
  );
}

export function LoteFichaWorkspace({
  lote,
  tab,
  onTab,
  mostrarGraficasResumen = true,
  modoOperativo = false,
}: {
  lote: Lote;
  tab: TabId;
  onTab: (siguiente: TabId) => void;
  mostrarGraficasResumen?: boolean;
  /** Ficha del estanque: indicadores en Resumen, Producción, Calidad de agua y Biofloc. */
  modoOperativo?: boolean;
}) {
  const tabActivo = tab;

  if (modoOperativo) {
    const tabOperativo: SeccionOperativa = TABS_OPERATIVOS_IDS.has(tabActivo)
      ? (tabActivo as SeccionOperativa)
      : "resumen";
    return (
      <>
        <div className="flex flex-wrap gap-2 border-t border-[var(--bf-border)] px-6 pt-5">
          {TABS_OPERATIVOS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tabOperativo === item.id ? "bf-btn-primary" : "bf-btn-secondary"}
              onClick={() => onTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <VistaOperativaAnalisis loteId={lote.id} seccion={tabOperativo} />
        <details className="mx-6 mb-6 rounded-xl border border-[var(--bf-border)] bg-white p-4">
          <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
            Historial de ciclos del estanque
          </summary>
          <div className="mt-4">
            <HistorialEstanqueTab estanqueId={lote.estanque_id} loteActualId={lote.id} />
          </div>
        </details>
      </>
    );
  }

  return (
    <>
      <div className="mt-4 flex flex-wrap gap-1 overflow-x-auto rounded-2xl border border-[var(--bf-border)] bg-white p-1 shadow-[0_1px_2px_rgba(16,40,33,0.04)]">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`whitespace-nowrap rounded-xl px-3 py-2 text-sm transition-colors ${
              tabActivo === item.id
                ? "bg-[var(--bf-accent-soft)] font-semibold text-[var(--bf-accent)]"
                : "text-[var(--bf-muted)] hover:bg-[var(--bf-chip)] hover:text-[var(--bf-ink)]"
            }`}
            onClick={() => onTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {tabActivo === "resumen" ? (
          <ResumenTab
            loteId={lote.id}
            observaciones={lote.observaciones}
            fechaCierre={lote.fecha_cierre}
            pesoInicial={lote.peso_inicial_promedio_g}
            onVerGraficas={() => onTab("produccion")}
            mostrarGraficasResumen={mostrarGraficasResumen}
          />
        ) : null}
        {tabActivo === "produccion" ? (
          <div className="space-y-8">
            <LoteAnalisisPanel loteId={lote.id} seccionFija="produccion" />
            <details className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
              <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
                Registros de producción
              </summary>
              <p className="mt-1 text-xs text-[var(--bf-muted)]">
                Biometrías, mortalidades y cosechas. Las gráficas de arriba usan el análisis del API.
              </p>
              <div className="mt-6 space-y-10">
                <BiometriasTab loteId={lote.id} loteActivo={lote.estado.nombre === "ACTIVO"} />
                <MortalidadesTab loteId={lote.id} loteActivo={lote.estado.nombre === "ACTIVO"} />
                <CosechasTab lote={lote} />
              </div>
            </details>
          </div>
        ) : null}
        {tabActivo === "agua" ? (
          <div className="space-y-8">
            <LoteAnalisisPanel loteId={lote.id} seccionFija="agua" />
            <details className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
              <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
                Registrar mediciones de agua
              </summary>
              <div className="mt-4">
                <AguaTab lote={lote} />
              </div>
            </details>
          </div>
        ) : null}
        {tabActivo === "biofloc" ? (
          <div className="space-y-8">
            <LoteAnalisisPanel loteId={lote.id} seccionFija="biofloc" />
            <details className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
              <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
                Registrar Biofloc
              </summary>
              <div className="mt-4">
                <BioflocTab lote={lote} />
              </div>
            </details>
          </div>
        ) : null}
        {tabActivo === "alimentacion" ? (
          <div className="space-y-8">
            <LoteAnalisisPanel loteId={lote.id} seccionFija="alimentacion" />
            <details className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
              <summary className="cursor-pointer font-display text-sm font-semibold text-[var(--bf-ink)]">
                Registrar alimentación
              </summary>
              <div className="mt-4">
                <AlimentacionTab lote={lote} />
              </div>
            </details>
          </div>
        ) : null}
        {tabActivo === "finanzas" ? <FinanzasTab loteId={lote.id} /> : null}
        {tabActivo === "historial" ? <HistorialEstanqueTab estanqueId={lote.estanque_id} loteActualId={lote.id} /> : null}
      </div>
    </>
  );
}

function HistorialEstanqueTab({ estanqueId, loteActualId }: { estanqueId: number; loteActualId: number }) {
  const query = useQuery({
    queryKey: ["analisis-estanque-historial", estanqueId],
    queryFn: () => getComparativoEstanques(false, { estanqueId, incluirHistorial: true }),
    refetchOnMount: "always",
  });
  if (query.isLoading) return <LoadingState label="Cargando ciclos del estanque…" />;
  if (query.isError) return <ErrorAlert message={apiErrorMessage(query.error)} />;
  const ciclos = query.data?.ciclos ?? [];
  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--bf-muted)]">
        Todos los ciclos usan los mismos cálculos congelados del backend. Los costos mostrados son únicamente gastos directamente imputados.
      </p>
      <DataTable
        rows={ciclos}
        rowKey={(row) => row.lote_id}
        empty="Este estanque no tiene ciclos registrados."
        columns={[
          {
            key: "lote",
            header: "Lote",
            render: (row) => (
              <Link
                className="font-medium text-[var(--bf-accent)] hover:underline"
                to={pathFichaEstanque(estanqueId, { loteId: row.lote_id })}
              >
                {row.lote_codigo}{row.lote_id === loteActualId ? " · actual" : ""}
              </Link>
            ),
          },
          { key: "estado", header: "Estado", render: (row) => (
            <StatusBadge
              label={row.estado_lote}
              tone={row.estado_lote === "ACTIVO" ? "ok" : "neutral"}
            />
          ) },
          { key: "especie", header: "Especie", render: (row) => row.especie },
          { key: "siembra", header: "Siembra", render: (row) => formatDate(row.fecha_siembra) },
          { key: "cierre", header: "Cierre", render: (row) => row.fecha_cierre ? formatDate(row.fecha_cierre) : "N/D" },
          { key: "biomasa", header: "Biomasa (kg)", render: (row) => row.productividad.biomasa_actual_kg == null ? "N/D" : formatNumber(row.productividad.biomasa_actual_kg, { maximumFractionDigits: 3 }) },
          { key: "produccion", header: "Cosechado (kg)", render: (row) => formatNumber(row.productividad.peso_cosechado_kg, { maximumFractionDigits: 3 }) },
          { key: "supervivencia", header: "Superv. %", render: (row) => row.productividad.supervivencia_porcentaje == null ? "N/D" : formatNumber(row.productividad.supervivencia_porcentaje, { maximumFractionDigits: 2 }) },
          { key: "fca", header: FCA_LABEL, render: (row) => row.eficiencia.fca_disponible ? <span title={FCA_HINT_ECONOMICO}>{formatNumber(row.eficiencia.fca, { maximumFractionDigits: 4 })}</span> : <span title={row.eficiencia.fca_motivo ?? undefined}>N/D</span> },
          { key: "ingresos", header: "Ingresos", render: (row) => formatCop(row.finanzas.ingresos_lote) },
          { key: "gastos", header: "Gastos directos", render: (row) => formatCop(row.finanzas.gastos_directos_lote) },
        ]}
      />
    </div>
  );
}

function nd(valor: string | number | null | undefined, digitos = 3): string {
  if (valor == null || valor === "") return "N/D";
  return formatNumber(valor, { minimumFractionDigits: digitos, maximumFractionDigits: digitos });
}

function GraficasResumen({
  data,
  onVerTodas,
}: {
  data: AnalisisLote;
  onVerTodas?: () => void;
}) {
  const puntosPeso = data.biometrias.map((fila) => ({
    etiqueta: formatDateTime(fila.fecha_hora),
    peso: toNumber(fila.peso_promedio_g),
    esperado: toNumber(fila.peso_esperado_g),
  }));
  const hayEsperado = puntosPeso.some((punto) => punto.esperado !== null);
  const puntosBiomasa = data.serie_biomasa.map((fila) => ({
    etiqueta: formatDateTime(fila.fecha_hora),
    biomasa: toNumber(fila.biomasa_kg),
  }));
  const puntosPoblacion = data.serie_poblacion.map((fila) => ({
    etiqueta: formatDateTime(fila.fecha_hora),
    poblacion: fila.poblacion_estimada,
    mortalidad: fila.mortalidad_acumulada,
    supervivencia: toNumber(fila.supervivencia_porcentaje),
  }));
  const puntosAlimento = data.alimentacion_real
    .filter((fila) => fila.convertible_a_kg && fila.acumulado_kg != null)
    .map((fila) => ({
      etiqueta: formatDateTime(fila.fecha_hora),
      acumulado: toNumber(fila.acumulado_kg),
    }));
  const biomasaActual = nd(data.indicadores.biomasa_actual_kg);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
          Gráficas principales
        </h2>
        {onVerTodas ? (
          <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={onVerTodas}>
            Ver producción completa
          </button>
        ) : null}
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <ChartCard
          title="Peso promedio vs tiempo"
          unidad="g"
          vacio={puntosPeso.length === 0}
          vacioMensaje="Sin datos suficientes para graficar. Falta registrar biometrías."
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
          title="Biomasa vs tiempo"
          unidad="kg"
          vacio={puntosBiomasa.length === 0}
          vacioMensaje={`Serie histórica de biomasa no disponible. Biomasa actual: ${biomasaActual}${
            biomasaActual === "N/D" ? ` · ${data.pendientes.biomasa_actual_kg ?? "SIN_BIOMETRIA"}` : " kg"
          }.`}
        >
          <TimeSeriesChart
            data={puntosBiomasa}
            series={[{ key: "biomasa", nombre: "Biomasa (kg)" }]}
            unidad="kg"
          />
        </ChartCard>
        <ChartCard
          title="Población y mortalidad acumulada"
          unidad="peces"
          vacio={puntosPoblacion.length === 0}
          vacioMensaje="El backend no entrega serie histórica de población para este lote."
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
          title="Alimento real acumulado"
          unidad="kg"
          vacio={puntosAlimento.length === 0}
          vacioMensaje="Sin datos suficientes para graficar. Falta alimentación convertible a kg."
        >
          <TimeSeriesChart
            data={puntosAlimento}
            series={[{ key: "acumulado", nombre: "Acumulado (kg)" }]}
            unidad="kg"
          />
        </ChartCard>
      </div>
    </div>
  );
}

function ResumenTab({
  loteId,
  observaciones,
  fechaCierre,
  pesoInicial,
  onVerGraficas,
  mostrarGraficasResumen = true,
}: {
  loteId: number;
  observaciones: string | null;
  fechaCierre: string | null;
  pesoInicial: number | null;
  onVerGraficas?: () => void;
  mostrarGraficasResumen?: boolean;
}) {
  const analisis = useQuery({
    queryKey: ["analisis-lote", loteId, "", ""],
    queryFn: () => getAnalisisLote(loteId),
  });
  const ind = analisis.data?.indicadores;
  const fin = analisis.data?.finanzas;

  return (
    <div className="space-y-6">
      {analisis.isLoading ? <LoadingState label="Cargando indicadores del lote…" /> : null}
      {analisis.isError ? <ErrorAlert message={apiErrorMessage(analisis.error)} /> : null}

      {ind ? (
        <section>
          <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
            Estado del cultivo
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Peces sembrados" value={formatNumber(ind.peces_sembrados)} />
            <KpiCard label="Población estimada" value={formatNumber(ind.poblacion_estimada)} />
            <KpiCard label="Peces cosechados" value={formatNumber(ind.peces_cosechados)} />
            <KpiCard label="Mortalidad acumulada" value={formatNumber(ind.mortalidad_acumulada)} />
            <KpiCard label="Supervivencia (%)" value={nd(ind.supervivencia_porcentaje, 2)} />
            <KpiCard label="Mortalidad (%)" value={nd(ind.mortalidad_porcentaje, 2)} />
            <KpiCard label="Días de cultivo" value={formatNumber(ind.dias_cultivo)} />
            <KpiCard label="Semana" value={formatNumber(ind.semana_cultivo)} />
            <KpiCard
              label="Biomasa inicial (kg)"
              value={nd(ind.biomasa_inicial_kg, 2)}
              hint={analisis.data?.pendientes.biomasa_inicial_kg}
            />
            <KpiCard
              label="Biomasa actual (kg)"
              value={nd(ind.biomasa_actual_kg, 2)}
              hint={analisis.data?.pendientes.biomasa_actual_kg}
            />
            <KpiCard
              label="Peso promedio (g)"
              value={nd(ind.peso_promedio_g)}
              hint={ind.peso_promedio_g == null ? "SIN_BIOMETRIA" : undefined}
            />
            <KpiCard
              label={FCA_LABEL}
              value={ind.fca_disponible ? nd(ind.fca, 4) : "N/D"}
              hint={
                ind.fca_disponible
                  ? fcaHintDisponible(fechaCierre)
                  : fcaHintNoDisponible(ind.fca_motivo)
              }
              title={FCA_HINT_ECONOMICO}
            />
            <KpiCard
              label="Ración diaria recomendada (kg)"
              value={nd(ind.racion_diaria_recomendada_kg)}
              hint={analisis.data?.pendientes.racion_diaria_recomendada_kg}
            />
            <KpiCard
              label="Raciones por día"
              value={
                ind.raciones_diarias_texto
                  ? ind.raciones_diarias_texto
                  : nd(ind.numero_raciones_diarias, 0)
              }
              hint={ind.raciones_diarias_texto ? undefined : analisis.data?.pendientes.numero_raciones_diarias}
            />
          </div>
        </section>
      ) : null}

      {mostrarGraficasResumen && analisis.data ? (
        <GraficasResumen data={analisis.data} onVerTodas={onVerGraficas} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
            Información del lote
          </h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Fecha de cierre</dt>
              <dd>{fechaCierre ? formatDate(fechaCierre) : "N/D"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Peso inicial promedio (g)</dt>
              <dd>{pesoInicial == null ? "N/D" : formatNumber(pesoInicial, { maximumFractionDigits: 3 })}</dd>
            </div>
            <div>
              <dt className="text-[var(--bf-muted)]">Observaciones</dt>
              <dd className="mt-1">{observaciones || "—"}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
            Resumen financiero del lote
          </h2>
          <p className="mt-1 text-xs text-[var(--bf-muted)]">
            Solo ingresos y gastos con lote_id. Costo completo, utilidad y margen permanecen N/D.
          </p>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt>Ingresos</dt>
              <dd>{fin ? formatCop(fin.ingresos_lote) : "…"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Gastos directos</dt>
              <dd>{fin ? formatCop(fin.gastos_directos_lote) : "…"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Balance directo</dt>
              <dd>{fin ? formatCop(Number(fin.ingresos_lote) - Number(fin.gastos_directos_lote)) : "…"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Costo completo / rentabilidad</dt>
              <dd title={fin?.costos_completos_motivo ?? fin?.utilidad_motivo}>N/D</dd>
            </div>
          </dl>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to={`/finanzas/ventas?lote_id=${loteId}`} className="bf-btn-secondary !py-1 text-xs">
              Ver Finanzas del lote
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function FinanzasTab({ loteId }: { loteId: number }) {
  const analisis = useQuery({
    queryKey: ["analisis-lote", loteId, "", ""],
    queryFn: () => getAnalisisLote(loteId),
  });
  const fin = analisis.data?.finanzas;

  return (
    <div className="space-y-4">
      {analisis.isLoading ? <LoadingState label="Cargando finanzas del lote…" /> : null}
      {analisis.isError ? <ErrorAlert message={apiErrorMessage(analisis.error)} /> : null}
      <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
          Finanzas imputadas
        </h2>
        <p className="mt-1 text-xs text-[var(--bf-muted)]">
          Solo ingresos y gastos con lote_id. Utilidad, margen y costo/kg permanecen N/D: el backend no
          prorratea costos incompletos.
        </p>
        {fin ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Ingresos" value={formatCop(fin.ingresos_lote)} hint={`${fin.ventas_registradas} venta(s)`} />
            <KpiCard label="Gastos directos" value={formatCop(fin.gastos_directos_lote)} hint={`${fin.gastos_registrados} gasto(s)`} />
            <KpiCard
              label="Balance directo"
              value={formatCop(Number(fin.ingresos_lote) - Number(fin.gastos_directos_lote))}
              hint="Ingresos − gastos imputados al lote. No es utilidad."
            />
            <KpiCard label="Costo completo" value="N/D" hint={fin.costos_completos_motivo} />
            <KpiCard label="Utilidad" value="N/D" hint={fin.utilidad_motivo} />
            <KpiCard label="Margen / rentabilidad" value="N/D" hint={fin.margen_motivo} />
          </div>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to={`/finanzas/ventas?lote_id=${loteId}`} className="bf-btn-primary !py-1 text-xs">
            Ver Finanzas del lote
          </Link>
          <Link to={`/finanzas/gastos?lote_id=${loteId}`} className="bf-btn-secondary !py-1 text-xs">
            Gastos del lote
          </Link>
        </div>
      </div>
    </div>
  );
}

function BiometriasTab({ loteId, loteActivo }: { loteId: number; loteActivo: boolean }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = loteActivo && can(user?.rol, "crearBiometria");
  const query = useQuery({ queryKey: ["biometrias", loteId], queryFn: () => listBiometrias(loteId) });
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad_muestra: "",
      peso_total_muestra_g: "",
      talla_promedio: "",
      unidad_talla: "",
      observaciones: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: BiometriaCreate) => createBiometria(data),
    onSuccess: async () => {
      setOpen(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["biometrias", loteId] });
      await invalidateAnalisis(queryClient);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <TabHeader
        title="Biometrías"
        hint="Registros inmutables. Sin PUT ni DELETE."
        action={
          puedeCrear ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  fecha_hora: toDatetimeLocalValue(),
                  cantidad_muestra: "",
                  peso_total_muestra_g: "",
                  talla_promedio: "",
                  unidad_talla: "",
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar biometría
            </button>
          ) : null
        }
      />
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay biometrías para este lote."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "muestra", header: "Cant. muestra", render: (row) => formatNumber(row.cantidad_muestra) },
            {
              key: "peso",
              header: "Peso total muestra (g)",
              render: (row) => formatNumber(row.peso_total_muestra_g, { maximumFractionDigits: 3 }),
            },
            {
              key: "talla",
              header: "Talla promedio",
              render: (row) =>
                row.talla_promedio == null
                  ? "N/D"
                  : `${formatNumber(row.talla_promedio, { maximumFractionDigits: 3 })}${row.unidad_talla ? ` ${row.unidad_talla}` : ""}`,
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar biometría" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            const talla = values.talla_promedio.trim();
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: fechaHora,
              cantidad_muestra: Number(values.cantidad_muestra),
              peso_total_muestra_g: Number(values.peso_total_muestra_g),
              talla_promedio: talla === "" ? null : Number(talla),
              unidad_talla: values.unidad_talla.trim() || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Cantidad de muestra">
            <input type="number" min="1" className="bf-input" {...form.register("cantidad_muestra", { valueAsNumber: true })} />
          </Field>
          <Field label="Peso total de la muestra en gramos">
            <input type="number" step="any" min="0.001" className="bf-input" {...form.register("peso_total_muestra_g", { required: true, valueAsNumber: true, min: 0.001 })} />
          </Field>
          <Field label="Talla promedio (opcional)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("talla_promedio")} />
          </Field>
          <Field label="Unidad de talla (opcional)">
            <input className="bf-input" {...form.register("unidad_talla")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function MortalidadesTab({ loteId, loteActivo }: { loteId: number; loteActivo: boolean }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = loteActivo && can(user?.rol, "crearMortalidad");
  const query = useQuery({ queryKey: ["mortalidades", loteId], queryFn: () => listMortalidades(loteId) });
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      causa: "",
      observaciones: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: MortalidadCreate) => createMortalidad(data),
    onSuccess: async () => {
      setOpen(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["mortalidades", loteId] });
      await invalidateAnalisis(queryClient);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <TabHeader
        title="Mortalidades"
        hint="Registro inmutable. Los tres roles pueden crear."
        action={
          puedeCrear ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  fecha_hora: toDatetimeLocalValue(),
                  cantidad: "",
                  causa: "",
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar mortalidad
            </button>
          ) : null
        }
      />
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay mortalidades para este lote."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "cantidad", header: "Cantidad", render: (row) => formatNumber(row.cantidad) },
            { key: "causa", header: "Causa", render: (row) => row.causa || "—" },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar mortalidad" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: fechaHora,
              cantidad: Number(values.cantidad),
              causa: values.causa.trim() || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Cantidad">
            <input type="number" min="1" className="bf-input" {...form.register("cantidad", { valueAsNumber: true })} />
          </Field>
          <Field label="Causa (opcional)">
            <input className="bf-input" {...form.register("causa")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function CosechasTab({ lote }: { lote: Lote }) {
  const loteId = lote.id;
  const loteActivo = lote.estado.nombre === "ACTIVO";
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = loteActivo && can(user?.rol, "crearCosecha");
  const query = useQuery({ queryKey: ["cosechas", loteId], queryFn: () => listCosechas(loteId) });
  const analisisQuery = useQuery({
    queryKey: ["analisis-lote", loteId, "", ""],
    queryFn: () => getAnalisisLote(loteId),
    enabled: open,
  });
  const disponible = analisisQuery.data?.indicadores.poblacion_estimada ?? null;
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad_peces: "",
      peso_total_kg: "",
      peso_promedio_g: "",
      observaciones: "",
    },
  });
  const cantidadWatch = Number(form.watch("cantidad_peces"));
  const restantesPreview =
    disponible != null && Number.isInteger(cantidadWatch) && cantidadWatch > 0
      ? disponible - cantidadWatch
      : null;

  const mutation = useMutation({
    mutationFn: (data: CosechaCreate) => createCosecha(data),
    onSuccess: async () => {
      setOpen(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["cosechas", loteId] });
      await queryClient.invalidateQueries({ queryKey: ["lote", loteId] });
      await queryClient.invalidateQueries({ queryKey: ["lotes"] });
      await invalidateAnalisis(queryClient);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <TabHeader
        title="Cosechas"
        hint="Registros inmutables. Peso total en kilogramos, peso promedio por pez en gramos."
        action={
          puedeCrear ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  fecha_hora: toDatetimeLocalValue(),
                  cantidad_peces: "",
                  peso_total_kg: "",
                  peso_promedio_g: "",
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar cosecha
            </button>
          ) : null
        }
      />
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay cosechas para este lote."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "peces", header: "Peces", render: (row) => formatNumber(row.cantidad_peces) },
            {
              key: "peso",
              header: "Peso total (kg)",
              render: (row) => formatNumber(row.peso_total_kg, { maximumFractionDigits: 3 }),
            },
            {
              key: "promedio",
              header: "Peso promedio (g)",
              render: (row) =>
                row.peso_promedio_g == null || row.peso_promedio_g === ""
                  ? "—"
                  : formatNumber(row.peso_promedio_g, { maximumFractionDigits: 3 }),
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar cosecha" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            const cantidadPeces = Number(values.cantidad_peces);
            const pesoTotalKg = Number(values.peso_total_kg);
            if (!Number.isInteger(cantidadPeces) || cantidadPeces <= 0) {
              setFormError("La cantidad de peces debe ser un entero mayor que 0.");
              return;
            }
            if (disponible != null && cantidadPeces > disponible) {
              setFormError(
                `No se pueden cosechar ${cantidadPeces} peces. La población disponible es ${disponible}.`,
              );
              return;
            }
            if (!Number.isFinite(pesoTotalKg) || pesoTotalKg <= 0) {
              setFormError("El peso total cosechado debe ser mayor que 0.");
              return;
            }
            const promedio = values.peso_promedio_g.trim();
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: fechaHora,
              cantidad_peces: cantidadPeces,
              peso_total_kg: pesoTotalKg,
              peso_promedio_g: promedio === "" ? null : Number(promedio),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <p className="text-sm text-[var(--bf-ink)]">
            Población disponible:{" "}
            <span className="font-semibold">
              {disponible == null ? "N/D" : `${formatNumber(disponible)} peces`}
            </span>
          </p>
          {restantesPreview != null && restantesPreview >= 0 ? (
            <p className="text-sm text-[var(--bf-muted)]">{mensajeRestantesCosecha(restantesPreview)}</p>
          ) : null}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Cantidad de peces">
            <input type="number" min="1" step="1" className="bf-input" {...form.register("cantidad_peces", { required: true })} />
          </Field>
          <Field label="Peso total en kilogramos">
            <input type="number" step="any" min="0.001" className="bf-input" {...form.register("peso_total_kg", { required: true })} />
          </Field>
          <Field label="Peso promedio por pez en gramos (opcional)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("peso_promedio_g")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function TabHeader({ title, hint, action }: { title: string; hint: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">{title}</h2>
        <p className="text-sm text-[var(--bf-muted)]">{hint}</p>
      </div>
      {action}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{label}</dt>
      <dd className="mt-1 text-lg font-medium text-[var(--bf-ink)]">{value}</dd>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-[var(--bf-ink)]">{label}</span>
      {children}
    </label>
  );
}

function AguaTab({ lote }: { lote: Lote }) {
  const parametrosQuery = useQuery({
    queryKey: ["parametros-agua"],
    queryFn: () => listParametrosAgua(true),
  });
  const refsQuery = useQuery({
    queryKey: ["referencias-agua", lote.especie_id, lote.etapa_productiva_id],
    queryFn: () =>
      listReferenciasAgua({
        especie_id: lote.especie_id,
        etapa_productiva_id: lote.etapa_productiva_id,
        solo_activos: true,
      }),
  });
  const medicionesQuery = useQuery({
    queryKey: ["mediciones-agua", lote.id],
    queryFn: () => listMedicionesAgua({ lote_id: lote.id }),
  });

  return (
    <AguaMedicionesPanel
      loteId={lote.id}
      lote={lote}
      lotes={[lote]}
      parametros={parametrosQuery.data ?? []}
      referencias={refsQuery.data ?? []}
      mediciones={medicionesQuery.data}
      loading={medicionesQuery.isLoading}
      error={medicionesQuery.error}
      onRetry={() => void medicionesQuery.refetch()}
      compact
    />
  );
}

function BioflocTab({ lote }: { lote: Lote }) {
  return (
    <div className="space-y-8">
      <MedicionesBioflocPanel loteId={lote.id} lotes={[lote]} compact />
      <AplicacionesBioflocPanel loteId={lote.id} lotes={[lote]} compact />
    </div>
  );
}

function AlimentacionTab({ lote }: { lote: Lote }) {
  return <AlimentacionPanel loteId={lote.id} lotes={[lote]} compact />;
}
