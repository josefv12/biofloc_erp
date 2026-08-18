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
import { LoteAnalisisPanel } from "./LoteAnalisisPanel";
import { AguaMedicionesPanel } from "../operacion/AguaPage";
import { AplicacionesBioflocPanel, MedicionesBioflocPanel } from "../operacion/BioflocPage";
import { AlimentacionPanel } from "../operacion/AlimentacionPage";
import { apiErrorMessage } from "../../utils/apiError";
import {
  datetimeLocalToIso,
  formatCop,
  formatDate,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import type { BiometriaCreate, CosechaCreate, Lote, MortalidadCreate } from "../../types/production";

type TabId = "resumen" | "analisis" | "historial" | "biometrias" | "mortalidades" | "cosechas" | "agua" | "biofloc" | "alimentacion";

const TABS: { id: TabId; label: string }[] = [
  { id: "resumen", label: "Resumen" },
  { id: "analisis", label: "Análisis" },
  { id: "historial", label: "Historial del estanque" },
  { id: "biometrias", label: "Biometrías" },
  { id: "mortalidades", label: "Mortalidades" },
  { id: "cosechas", label: "Cosechas" },
  { id: "agua", label: "Agua" },
  { id: "biofloc", label: "Biofloc" },
  { id: "alimentacion", label: "Alimentación" },
];

const TAB_IDS = new Set<string>(TABS.map((item) => item.id));

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
  const tabSolicitada = searchParams.get("tab");
  const tab: TabId = tabSolicitada && TAB_IDS.has(tabSolicitada) ? (tabSolicitada as TabId) : "resumen";

  // La pestaña vive en la URL para que la ficha sea compartible y el botón
  // atrás del navegador recorra las pestañas visitadas.
  function setTab(siguiente: TabId) {
    const params = new URLSearchParams(searchParams);
    params.set("tab", siguiente);
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
              <Link to="/produccion/estanques?comparativo=1" className="text-[var(--bf-accent)] hover:underline">
                Estanque {estanqueLabel}
              </Link>
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

      <div className="mt-4 flex flex-wrap gap-1 overflow-x-auto border-b border-[var(--bf-border)]">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`whitespace-nowrap px-3 py-2 text-sm ${
              tab === item.id
                ? "border-b-2 border-[var(--bf-accent)] font-medium text-[var(--bf-ink)]"
                : "text-[var(--bf-muted)] hover:text-[var(--bf-ink)]"
            }`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {tab === "resumen" ? <ResumenTab loteId={lote.id} observaciones={lote.observaciones} fechaCierre={lote.fecha_cierre} pesoInicial={lote.peso_inicial_promedio_g} /> : null}
        {tab === "analisis" ? <LoteAnalisisPanel loteId={lote.id} /> : null}
        {tab === "historial" ? <HistorialEstanqueTab estanqueId={lote.estanque_id} loteActualId={lote.id} /> : null}
        {tab === "biometrias" ? <BiometriasTab loteId={lote.id} /> : null}
        {tab === "mortalidades" ? <MortalidadesTab loteId={lote.id} /> : null}
        {tab === "cosechas" ? <CosechasTab loteId={lote.id} /> : null}
        {tab === "agua" ? <AguaTab lote={lote} /> : null}
        {tab === "biofloc" ? <BioflocTab lote={lote} /> : null}
        {tab === "alimentacion" ? <AlimentacionTab lote={lote} /> : null}
      </div>
    </div>
  );
}

function HistorialEstanqueTab({ estanqueId, loteActualId }: { estanqueId: number; loteActualId: number }) {
  const query = useQuery({
    queryKey: ["analisis-estanque-historial", estanqueId],
    queryFn: () => getComparativoEstanques(false, { estanqueId, incluirHistorial: true }),
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
              <Link className="font-medium text-[var(--bf-accent)] hover:underline" to={`/produccion/lotes/${row.lote_id}?tab=analisis`}>
                {row.lote_codigo}{row.lote_id === loteActualId ? " · actual" : ""}
              </Link>
            ),
          },
          { key: "estado", header: "Estado", render: (row) => row.estado_lote },
          { key: "especie", header: "Especie", render: (row) => row.especie },
          { key: "siembra", header: "Siembra", render: (row) => formatDate(row.fecha_siembra) },
          { key: "cierre", header: "Cierre", render: (row) => row.fecha_cierre ? formatDate(row.fecha_cierre) : "N/D" },
          { key: "biomasa", header: "Biomasa (kg)", render: (row) => row.productividad.biomasa_actual_kg == null ? "N/D" : formatNumber(row.productividad.biomasa_actual_kg, { maximumFractionDigits: 3 }) },
          { key: "produccion", header: "Cosechado (kg)", render: (row) => formatNumber(row.productividad.peso_cosechado_kg, { maximumFractionDigits: 3 }) },
          { key: "supervivencia", header: "Superv. %", render: (row) => row.productividad.supervivencia_porcentaje == null ? "N/D" : formatNumber(row.productividad.supervivencia_porcentaje, { maximumFractionDigits: 2 }) },
          { key: "fca", header: "FCA", render: (row) => row.eficiencia.fca_disponible ? formatNumber(row.eficiencia.fca, { maximumFractionDigits: 4 }) : <span title={row.eficiencia.fca_motivo ?? undefined}>N/D</span> },
          { key: "ingresos", header: "Ingresos", render: (row) => formatCop(row.finanzas.ingresos_lote) },
          { key: "gastos", header: "Gastos directos", render: (row) => formatCop(row.finanzas.gastos_directos_lote) },
        ]}
      />
    </div>
  );
}

function nd(valor: string | number | null | undefined, digitos = 3): string {
  if (valor === null || valor === undefined || valor === "") return "N/D";
  return formatNumber(valor, { maximumFractionDigits: digitos });
}

function ResumenTab({
  loteId,
  observaciones,
  fechaCierre,
  pesoInicial,
}: {
  loteId: number;
  observaciones: string | null;
  fechaCierre: string | null;
  pesoInicial: number | null;
}) {
  const analisis = useQuery({
    queryKey: ["analisis-lote", loteId, "", ""],
    queryFn: () => getAnalisisLote(loteId),
  });
  const bio = useQuery({ queryKey: ["biometrias", loteId], queryFn: () => listBiometrias(loteId) });
  const mort = useQuery({ queryKey: ["mortalidades", loteId], queryFn: () => listMortalidades(loteId) });
  const cos = useQuery({ queryKey: ["cosechas", loteId], queryFn: () => listCosechas(loteId) });
  const ind = analisis.data?.indicadores;
  const fin = analisis.data?.finanzas;

  return (
    <div className="space-y-4">
      {analisis.isLoading ? <LoadingState label="Cargando indicadores del lote…" /> : null}
      {analisis.isError ? <ErrorAlert message={apiErrorMessage(analisis.error)} /> : null}
      {ind ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label="Días de cultivo" value={formatNumber(ind.dias_cultivo)} hint={`Semana ${ind.semana_cultivo}`} />
          <KpiCard label="Población estimada" value={formatNumber(ind.poblacion_estimada)} />
          <KpiCard label="Peso promedio (g)" value={nd(ind.peso_promedio_g)} hint={ind.peso_promedio_g == null ? "SIN_BIOMETRIA" : undefined} />
          <KpiCard label="Biomasa actual (kg)" value={nd(ind.biomasa_actual_kg)} hint={analisis.data?.pendientes.biomasa_actual_kg} />
          <KpiCard label="Supervivencia (%)" value={nd(ind.supervivencia_porcentaje, 2)} />
          <KpiCard label="Mortalidad (%)" value={nd(ind.mortalidad_porcentaje, 2)} />
          <KpiCard label="FCA" value={ind.fca_disponible ? nd(ind.fca, 4) : "N/D"} hint={ind.fca_motivo ?? undefined} />
          <KpiCard
            label="Productividad Δ kg"
            value={nd(analisis.data?.productividad.ganancia_biomasa_kg)}
            hint={analisis.data?.productividad.motivos.ganancia_biomasa_kg}
          />
        </div>
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
            Finanzas imputadas
          </h2>
          <p className="mt-1 text-xs text-[var(--bf-muted)]">
            Solo ingresos y gastos con lote_id. Utilidad y costo/kg permanecen N/D.
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
              <dt>Utilidad / margen</dt>
              <dd>N/D</dd>
            </div>
          </dl>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to={`/finanzas/ventas?lote_id=${loteId}`} className="bf-btn-secondary !py-1 text-xs">
              Ventas del lote
            </Link>
            <Link to={`/finanzas/gastos?lote_id=${loteId}`} className="bf-btn-secondary !py-1 text-xs">
              Gastos del lote
            </Link>
          </div>
        </div>
        <div className="rounded-xl border border-[var(--bf-border)] bg-white p-4">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
            Registros de seguimiento
          </h2>
          <p className="mt-1 text-xs text-[var(--bf-muted)]">Conteo de filas del API. No es población estimada.</p>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt>Biometrías</dt>
              <dd>{bio.data ? formatNumber(bio.data.length) : "…"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Mortalidades</dt>
              <dd>{mort.data ? formatNumber(mort.data.length) : "…"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Cosechas</dt>
              <dd>{cos.data ? formatNumber(cos.data.length) : "…"}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}

function BiometriasTab({ loteId }: { loteId: number }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = can(user?.rol, "crearBiometria");
  const query = useQuery({ queryKey: ["biometrias", loteId], queryFn: () => listBiometrias(loteId) });
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad_muestra: 1,
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
                  cantidad_muestra: 1,
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
                  ? "—"
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
            const talla = values.talla_promedio.trim();
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
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

function MortalidadesTab({ loteId }: { loteId: number }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = can(user?.rol, "crearMortalidad");
  const query = useQuery({ queryKey: ["mortalidades", loteId], queryFn: () => listMortalidades(loteId) });
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad: 1,
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
                  cantidad: 1,
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
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
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

function CosechasTab({ loteId }: { loteId: number }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeCrear = can(user?.rol, "crearCosecha");
  const query = useQuery({ queryKey: ["cosechas", loteId], queryFn: () => listCosechas(loteId) });
  const form = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      cantidad_peces: 1,
      peso_total_kg: "",
      peso_promedio_g: "",
      observaciones: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: CosechaCreate) => createCosecha(data),
    onSuccess: async () => {
      setOpen(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["cosechas", loteId] });
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
                  cantidad_peces: 1,
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
            const promedio = values.peso_promedio_g.trim();
            mutation.mutate({
              lote_id: loteId,
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
              cantidad_peces: Number(values.cantidad_peces),
              peso_total_kg: Number(values.peso_total_kg),
              peso_promedio_g: promedio === "" ? null : Number(promedio),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Cantidad de peces">
            <input type="number" min="1" className="bf-input" {...form.register("cantidad_peces", { valueAsNumber: true })} />
          </Field>
          <Field label="Peso total en kilogramos">
            <input type="number" step="any" min="0.001" className="bf-input" {...form.register("peso_total_kg", { required: true, valueAsNumber: true, min: 0.001 })} />
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
