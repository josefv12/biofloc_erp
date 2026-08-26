import { Link, useParams, useSearchParams } from "react-router-dom";
import { useEffect, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ErrorAlert } from "../../components/ErrorAlert";
import { ContextoAlimentacionPanel } from "../../components/alimentacion/ContextoAlimentacionPanel";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { useAuth } from "../../auth/AuthProvider";
import { getAnalisisLote } from "../../api/analisis";
import { getContextoAlimentacionLote } from "../../api/alimentacionReferencia";
import {
  createBiometria,
  createCosecha,
  createMortalidad,
  getEstanque,
  getLote,
  listLotes,
} from "../../api/production";
import {
  createAlimentacion,
  createAplicacionBiofloc,
  createMedicionBiofloc,
  createMedicionAgua,
  listAplicacionesBiofloc,
  listMedicionesBiofloc,
  listParametrosAgua,
  listProductosActivos,
  listTiposAplicacionBiofloc,
  listUnidades,
} from "../../api/operations";
import { apiErrorMessage } from "../../utils/apiError";
import { ChevronLeft } from "lucide-react";
import { FichaBadge, FichaLabel, FichaMetric } from "../../components/ficha/FichaMetric";
import {
  etiquetaProducto,
  formatDate,
  formatNumber,
  toDatetimeLocalValue,
  withFechaHoraIso,
} from "../../utils/format";
import {
  fechaLocalISO,
  mensajeRestantesCosecha,
  num,
  PESO_OBJETIVO_COSECHA_G,
  proyectarCosecha,
} from "../../utils/indicadoresProduccion";
import { can } from "../../utils/rbac";
import { PATH_COMPARACION } from "./fichaPaths";
import { LoteFichaWorkspace, parseLoteFichaTab, type LoteFichaTabId } from "./LoteFichaPage";
import type { Lote } from "../../types/production";
import type { BiometriaCreate, CosechaCreate, MortalidadCreate } from "../../types/production";
import type {
  AlimentacionCreate,
  AplicacionBioflocCreate,
  MedicionAguaCreate,
  MedicionBioflocCreate,
} from "../../types/operations";
import type { AnalisisIndicadores } from "../../types/analisis";

function elegirLote(lotes: Lote[], loteSolicitado: number | null): Lote | undefined {
  if (loteSolicitado) {
    const pedido = lotes.find((lote) => lote.id === loteSolicitado);
    if (pedido) return pedido;
  }
  return lotes.find((lote) => lote.estado.nombre === "ACTIVO") ?? lotes[0];
}

function nd(valor: string | number | null | undefined, digitos = 3): string {
  if (valor === null || valor === undefined || valor === "") return "N/D";
  return formatNumber(valor, { maximumFractionDigits: digitos });
}

export function EstanqueFichaPage() {
  const { user } = useAuth();
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const estanqueId = Number(id);
  const invalidId = !Number.isInteger(estanqueId) || estanqueId <= 0;
  const loteSolicitado = Number(searchParams.get("lote"));
  const loteParam = Number.isInteger(loteSolicitado) && loteSolicitado > 0 ? loteSolicitado : null;
  const tab = parseLoteFichaTab(searchParams.get("tab"), "resumen");
  const queryClient = useQueryClient();

  const estanqueQuery = useQuery({
    queryKey: ["estanque", estanqueId],
    queryFn: () => getEstanque(estanqueId),
    enabled: !invalidId,
  });
  const lotesQuery = useQuery({
    queryKey: ["lotes", estanqueId],
    queryFn: () => listLotes(estanqueId),
    enabled: !invalidId,
  });

  const lotes = [...(lotesQuery.data ?? [])].sort((a, b) => b.fecha_siembra.localeCompare(a.fecha_siembra));
  const loteResumen = elegirLote(lotes, loteParam);
  const loteQuery = useQuery({
    queryKey: ["lote", loteResumen?.id],
    queryFn: () => getLote(loteResumen!.id),
    enabled: Boolean(loteResumen?.id),
  });
  const lote = loteQuery.data ?? loteResumen;
  const analisisQuery = useQuery({
    queryKey: ["analisis-lote", lote?.id, "", ""],
    queryFn: () => getAnalisisLote(lote!.id),
    enabled: Boolean(lote?.id),
  });
  const analisis = analisisQuery.data;
  const ind = analisis?.indicadores;

  function ndFixed(value: string | number | null | undefined, digitos: number): string {
    if (value === null || value === undefined || value === "") return "N/D";
    return formatNumber(value, { minimumFractionDigits: digitos, maximumFractionDigits: digitos });
  }

  const pesoInicialPreferidoG = ind?.peso_inicial_g ?? lote?.peso_inicial_promedio_g ?? null;

  type ModalAccion = "alimentar" | "biometria" | "mortalidad" | "agua" | "biofloc" | "cosechar";
  const [modalAccion, setModalAccion] = useState<ModalAccion | null>(null);

  async function refrescarPostOperacion() {
    if (!lote?.id) return;
    await queryClient.invalidateQueries({ queryKey: ["analisis-lote", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] });
    await queryClient.invalidateQueries({ queryKey: ["analisis-estanque-historial", estanqueId] });

    // Historial / tablas de registros
    await queryClient.invalidateQueries({ queryKey: ["alimentaciones", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["biometrias", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["mortalidades", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["cosechas", lote.id] });

    // Calidad de agua + Biofloc
    await queryClient.invalidateQueries({ queryKey: ["mediciones-agua", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["mediciones-biofloc", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["aplicaciones-biofloc", lote.id] });

    // Inventario (si aplica)
    await queryClient.invalidateQueries({ queryKey: ["stock"] });

    // En caso de cosecha: lote/estanques pueden cambiar de estado
    await queryClient.invalidateQueries({ queryKey: ["lotes", estanqueId] });
    await queryClient.invalidateQueries({ queryKey: ["lote", lote.id] });
    await queryClient.invalidateQueries({ queryKey: ["estanque", estanqueId] });
  }

  function setTab(siguiente: LoteFichaTabId) {
    const params = new URLSearchParams(searchParams);
    params.set("tab", siguiente);
    params.delete("seccion");
    setSearchParams(params, { replace: false });
  }

  function setLote(loteId: number) {
    const params = new URLSearchParams(searchParams);
    params.set("lote", String(loteId));
    if (!params.get("tab")) params.set("tab", "resumen");
    params.delete("seccion");
    setSearchParams(params, { replace: false });
  }

  if (invalidId) {
    return <ErrorAlert message="Identificador de estanque inválido." />;
  }
  if (estanqueQuery.isLoading || lotesQuery.isLoading) {
    return <LoadingState label="Cargando ficha del estanque…" />;
  }
  if (estanqueQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(estanqueQuery.error)} />
        <Link to={PATH_COMPARACION} className="bf-btn-secondary inline-flex">
          Volver a comparación
        </Link>
      </div>
    );
  }

  const estanque = estanqueQuery.data;
  if (!estanque) return null;

  const especie = lote?.especie.nombre_comun ?? "Sin lote";
  const loteCodigo = lote?.codigo ?? "Sin lote";
  const estadoCultivo = lote
    ? lote.estado.nombre
    : estanque.activo
      ? estanque.estado.nombre
      : "Inactivo";
  const estadoTone =
    lote?.estado.nombre === "ACTIVO" || (estanque.activo && !lote) ? "ok" : "neutral";
  const proyeccion = lote && ind
    ? proyectarCosecha({
        fechaSiembra: lote.fecha_siembra,
        diasCultivo: ind.dias_cultivo,
        pesoActualG: num(ind.peso_promedio_g),
        gananciaDiariaG: num(ind.ganancia_diaria_g),
        poblacion: ind.poblacion_estimada,
      })
    : lote
      ? proyectarCosecha({
          fechaSiembra: lote.fecha_siembra,
          diasCultivo: 0,
          pesoActualG: null,
          gananciaDiariaG: null,
          poblacion: null,
        })
      : null;

  const btnAccion =
    "rounded-full py-2.5 text-sm font-medium border border-[var(--bf-border)] text-[var(--bf-ink)] bg-white hover:bg-[var(--bf-chip)]";
  const btnAccionPrimario =
    "rounded-full py-2.5 text-sm font-semibold text-white bg-[var(--bf-accent)] shadow-[0_8px_18px_rgba(31,107,84,0.22)] hover:brightness-105";

  return (
    <div>
      <Link
        to={PATH_COMPARACION}
        className="inline-flex items-center gap-1 text-sm text-[var(--bf-accent)] hover:underline"
      >
        <ChevronLeft size={16} /> Estanques
      </Link>

      <div className="mt-3 overflow-hidden rounded-2xl border border-[var(--bf-border)] bg-white shadow-[0_1px_2px_rgba(16,40,33,0.04),0_12px_32px_rgba(16,40,33,0.06)]">
        <div className="p-6 pb-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <FichaLabel>Estanque</FichaLabel>
              <h1 className="text-3xl font-extrabold text-[var(--bf-ink)]">{estanque.codigo}</h1>
              <p className="mt-1 text-sm text-gray-600">
                {especie} · {loteCodigo}
              </p>
              <p className="text-sm text-gray-600">{estanque.nombre}</p>
            </div>
            <FichaBadge tone={estadoTone}>{estadoCultivo}</FichaBadge>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <FichaMetric
              label="Días de cultivo"
              value={ind ? formatNumber(ind.dias_cultivo) : analisisQuery.isLoading ? "…" : "N/D"}
            />
            <FichaMetric
              label="Semana"
              value={ind ? formatNumber(ind.semana_cultivo) : analisisQuery.isLoading ? "…" : "N/D"}
            />
            <FichaMetric label="Etapa" value={lote?.etapa_productiva.nombre ?? "N/D"} />
            <FichaMetric
              label={proyeccion?.usaPrediccionCrecimiento ? "Cosecha estimada" : "Fecha máxima de ciclo"}
              value={
                proyeccion?.usaPrediccionCrecimiento && proyeccion.fechaCosechaEstimada
                  ? formatDate(fechaLocalISO(proyeccion.fechaCosechaEstimada))
                  : proyeccion?.fechaMaximaCiclo
                    ? formatDate(fechaLocalISO(proyeccion.fechaMaximaCiclo))
                    : "N/D"
              }
              sub={
                proyeccion
                  ? proyeccion.usaPrediccionCrecimiento
                    ? `Fecha máxima de ciclo: ${proyeccion.fechaMaximaCiclo ? formatDate(fechaLocalISO(proyeccion.fechaMaximaCiclo)) : "N/D"} · Objetivo de peso: ${PESO_OBJETIVO_COSECHA_G} g`
                    : `Estimación de calendario (24 semanas), no predicción de crecimiento. Objetivo de peso: ${PESO_OBJETIVO_COSECHA_G} g`
                  : undefined
              }
            />
          </div>
        </div>

        {lote?.estado.nombre === "ACTIVO" ? (
          <div className="grid grid-cols-2 gap-2.5 px-6 pb-5 md:grid-cols-3">
            {can(user?.rol, "registrarAlimentacion") ? (
              <button type="button" className={btnAccionPrimario} onClick={() => setModalAccion("alimentar")}>
                Alimentar
              </button>
            ) : null}
            {can(user?.rol, "crearBiometria") ? (
              <button type="button" className={btnAccion} onClick={() => setModalAccion("biometria")}>
                Biometría
              </button>
            ) : null}
            {can(user?.rol, "crearMortalidad") ? (
              <button type="button" className={btnAccion} onClick={() => setModalAccion("mortalidad")}>
                Mortalidad
              </button>
            ) : null}
            {can(user?.rol, "registrarAgua") ? (
              <button type="button" className={btnAccion} onClick={() => setModalAccion("agua")}>
                Medir agua
              </button>
            ) : null}
            {can(user?.rol, "registrarBiofloc") ? (
              <button type="button" className={btnAccion} onClick={() => setModalAccion("biofloc")}>
                Biofloc
              </button>
            ) : null}
            {can(user?.rol, "crearCosecha") ? (
              <button type="button" className={btnAccionPrimario} onClick={() => setModalAccion("cosechar")}>
                Cosechar
              </button>
            ) : null}
          </div>
        ) : null}

        {ind ? (
          <div className="border-t border-[var(--bf-border)] px-6 pb-6 pt-5">
            <FichaLabel>Siembra</FichaLabel>
            <div className="mt-3 grid grid-cols-2 gap-6">
              <FichaMetric label="Peso inicial" value={ndFixed(pesoInicialPreferidoG, 2)} unit="g" />
              <FichaMetric label="Fecha de siembra" value={lote ? formatDate(lote.fecha_siembra) : "N/D"} />
            </div>
          </div>
        ) : null}

        {lotes.length > 0 ? (
          <div className="border-t border-[var(--bf-border)] px-6 py-4">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-[var(--bf-ink)]">Ciclo del estanque</span>
              <select
                className="bf-input max-w-xl"
                value={lote?.id ?? ""}
                onChange={(event) => setLote(Number(event.target.value))}
              >
                {lotes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.codigo} · {item.especie.nombre_comun} · {item.estado.nombre} · siembra{" "}
                    {formatDate(item.fecha_siembra)}
                    {item.fecha_cierre ? ` · cierre ${formatDate(item.fecha_cierre)}` : ""}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-[var(--bf-muted)]">
                Cada ciclo conserva su propio análisis. No se mezclan lotes.
              </span>
            </label>
          </div>
        ) : null}

        {lotesQuery.isError ? (
          <div className="px-6 pb-4">
            <ErrorAlert message={apiErrorMessage(lotesQuery.error)} />
          </div>
        ) : null}

        {!loteResumen ? (
          <p className="px-6 pb-8 pt-2 text-center text-sm text-[var(--bf-muted)]">
            Este estanque no tiene lotes. No hay indicadores ni gráficas que mostrar.
          </p>
        ) : loteQuery.isLoading && !lote ? (
          <div className="px-6 pb-6">
            <LoadingState label="Cargando lote del estanque…" />
          </div>
        ) : loteQuery.isError ? (
          <div className="px-6 pb-6">
            <ErrorAlert message={apiErrorMessage(loteQuery.error)} />
          </div>
        ) : lote ? (
          <div>
            <LoteFichaWorkspace lote={lote} tab={tab} onTab={setTab} mostrarGraficasResumen={false} modoOperativo />

            {modalAccion === "alimentar" ? (
              <AlimentarModal
                loteId={lote.id}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}

            {modalAccion === "biometria" ? (
              <BiometriaModal
                loteId={lote.id}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}

            {modalAccion === "mortalidad" ? (
              <MortalidadModal
                loteId={lote.id}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}

            {modalAccion === "agua" ? (
              <AguaModal
                loteId={lote.id}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}

            {modalAccion === "biofloc" ? (
              <BioflocModal
                loteId={lote.id}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}

            {modalAccion === "cosechar" ? (
              <CosechaModal
                lote={lote}
                estanque={estanque}
                ind={analisisQuery.data?.indicadores}
                open
                onClose={() => setModalAccion(null)}
                onSaved={async () => {
                  await refrescarPostOperacion();
                  setModalAccion(null);
                }}
              />
            ) : null}
          </div>
        ) : null}
      </div>
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

function AlimentarModal({
  open,
  loteId,
  onClose,
  onSaved,
}: {
  open: boolean;
  loteId: number;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const productosQuery = useQuery({ queryKey: ["productos-activos"], queryFn: listProductosActivos });
  const unidadesQuery = useQuery({ queryKey: ["unidades"], queryFn: listUnidades });
  const contextoQuery = useQuery({
    queryKey: ["contexto-alimentacion", loteId],
    queryFn: () => getContextoAlimentacionLote(loteId),
    enabled: open,
  });
  const ref = contextoQuery.data?.referencia_activa;
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      lote_id: loteId,
      producto_id: 0,
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      observaciones: "",
    },
  });

  useEffect(() => {
    if ((productosQuery.data ?? []).length === 0) return;
    const primero = productosQuery.data?.[0]?.id ?? 0;
    const actual = form.getValues("producto_id");
    if (actual === 0 && primero) {
      form.reset({
        ...form.getValues(),
        producto_id: primero,
      });
    }
  }, [productosQuery.data]);

  const mutation = useMutation({
    mutationFn: (data: AlimentacionCreate) => createAlimentacion(data),
    onSuccess: async () => {
      setFormError(null);
      await onSaved();
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  const productos = productosQuery.data ?? [];
  const unidades = new Map((unidadesQuery.data ?? []).map((row) => [row.id, row]));
  const productoIdSeleccionado = form.watch("producto_id");
  const productoSeleccionado = productos.find((row) => row.id === Number(productoIdSeleccionado));
  const simboloUnidad = productoSeleccionado
    ? unidades.get(productoSeleccionado.unidad_id)?.simbolo
    : undefined;
  const etiquetaCantidad = simboloUnidad
    ? `Cantidad suministrada (${simboloUnidad})`
    : "Cantidad suministrada";

  return (
    <Modal open={open} title="Registrar alimentación" onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={form.handleSubmit((values) => {
          const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
          if (!fechaHora) return;
          mutation.mutate({
            lote_id: loteId,
            producto_id: Number(values.producto_id),
            fecha_hora: fechaHora,
            cantidad: Number(values.cantidad),
            observaciones: values.observaciones.trim() || null,
          });
        })}
      >
        {formError ? <ErrorAlert message={formError} /> : null}
        {contextoQuery.isLoading ? (
          <p className="text-sm text-[var(--bf-muted)]">Calculando ración recomendada…</p>
        ) : ref ? (
          <ContextoAlimentacionPanel ref={ref} />
        ) : contextoQuery.isSuccess ? (
          <p className="text-sm text-[var(--bf-muted)]">N/D — Sin referencia configurada.</p>
        ) : null}
        {productosQuery.isLoading ? <LoadingState label="Cargando productos…" /> : null}

        <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />

        <Field label="Producto / alimento">
          <select className="bf-input" {...form.register("producto_id", { valueAsNumber: true, required: true })}>
            {productos.map((row) => (
              <option key={row.id} value={row.id}>
                {etiquetaProducto(row.nombre, row.codigo)}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Fecha y hora">
          <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
        </Field>

        <Field label={etiquetaCantidad}>
          <input type="number" step="any" min="0.0001" className="bf-input" {...form.register("cantidad", { required: true })} />
        </Field>

        <Field label="Observaciones">
          <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
        </Field>

        <p className="text-xs text-[var(--bf-muted)]">El inventario se actualizará automáticamente al registrar.</p>

        <button
          type="submit"
          className="bf-btn-primary"
          disabled={mutation.isPending || productos.length === 0}
        >
          {mutation.isPending ? "Guardando…" : "Registrar alimentación"}
        </button>
      </form>
    </Modal>
  );
}

function BiometriaModal({
  open,
  loteId,
  onClose,
  onSaved,
}: {
  open: boolean;
  loteId: number;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);

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
      setFormError(null);
      await onSaved();
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  return (
    <Modal open={open} title="Registrar biometría" onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={form.handleSubmit((values) => {
          const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
          if (!fechaHora) return;
          mutation.mutate({
            lote_id: loteId,
            fecha_hora: fechaHora,
            cantidad_muestra: Number(values.cantidad_muestra),
            peso_total_muestra_g: Number(values.peso_total_muestra_g),
            talla_promedio: values.talla_promedio.trim() === "" ? null : Number(values.talla_promedio),
            unidad_talla: values.unidad_talla.trim() || null,
            observaciones: values.observaciones.trim() || null,
          });
        })}
      >
        {formError ? <ErrorAlert message={formError} /> : null}

        <Field label="Fecha y hora">
          <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
        </Field>

        <Field label="Cantidad de peces muestreados">
          <input type="number" min="1" className="bf-input" {...form.register("cantidad_muestra", { valueAsNumber: true, required: true })} />
        </Field>

        <Field label="Peso total de la muestra (g)">
          <input
            type="number"
            step="any"
            min="0.001"
            className="bf-input"
            {...form.register("peso_total_muestra_g", { valueAsNumber: true, required: true, min: 0.001 })}
          />
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
  );
}

function MortalidadModal({
  open,
  loteId,
  onClose,
  onSaved,
}: {
  open: boolean;
  loteId: number;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);

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
      setFormError(null);
      await onSaved();
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  return (
    <Modal open={open} title="Registrar mortalidad" onClose={onClose}>
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
          <input type="number" min="1" className="bf-input" {...form.register("cantidad", { valueAsNumber: true, required: true })} />
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
  );
}

function AguaModal({
  open,
  loteId,
  onClose,
  onSaved,
}: {
  open: boolean;
  loteId: number;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const parametrosQuery = useQuery({ queryKey: ["parametros-agua"], queryFn: () => listParametrosAgua(true) });
  const [formError, setFormError] = useState<string | null>(null);

  const parametros = parametrosQuery.data ?? [];

  const form = useForm({
    defaultValues: {
      lote_id: loteId,
      parametro_id: 0,
      fecha_hora: toDatetimeLocalValue(),
      valor: "",
      observaciones: "",
    },
  });

  useEffect(() => {
    if (parametros.length === 0) return;
    const primero = parametros[0]?.id ?? 0;
    const actual = form.getValues("parametro_id");
    if (actual === 0 && primero) {
      form.reset({
        ...form.getValues(),
        parametro_id: primero,
      });
    }
  }, [parametrosQuery.data]);

  const mutation = useMutation({
    mutationFn: (data: MedicionAguaCreate) => createMedicionAgua(data),
    onSuccess: async () => {
      setFormError(null);
      await onSaved();
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  return (
    <Modal open={open} title="Registrar medición de agua" onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={form.handleSubmit((values) => {
          const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
          if (!fechaHora) return;
          mutation.mutate({
            lote_id: loteId,
            parametro_id: Number(values.parametro_id),
            fecha_hora: fechaHora,
            valor: Number(values.valor),
            observaciones: values.observaciones.trim() || null,
          });
        })}
      >
        {formError ? <ErrorAlert message={formError} /> : null}

        {parametrosQuery.isLoading ? <LoadingState label="Cargando parámetros…" /> : null}

        <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />

        <Field label="Parámetro">
          <select className="bf-input" {...form.register("parametro_id", { valueAsNumber: true, required: true })}>
            {parametros.map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre} ({row.unidad})
              </option>
            ))}
          </select>
        </Field>

        <Field label="Fecha y hora">
          <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
        </Field>

        <Field label="Valor">
          <input type="number" step="any" min="0" className="bf-input" {...form.register("valor", { valueAsNumber: true, required: true })} />
        </Field>

        <Field label="Observaciones">
          <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
        </Field>

        <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || parametros.length === 0}>
          {mutation.isPending ? "Guardando…" : "Registrar"}
        </button>
      </form>
    </Modal>
  );
}

function BioflocModal({
  open,
  loteId,
  onClose,
  onSaved,
}: {
  open: boolean;
  loteId: number;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [modo, setModo] = useState<"aplicacion" | "medicion">("aplicacion");
  const tiposQuery = useQuery({ queryKey: ["tipos-aplicacion-biofloc"], queryFn: () => listTiposAplicacionBiofloc(true) });
  const productosQuery = useQuery({ queryKey: ["productos-activos"], queryFn: listProductosActivos });
  const medicionesQuery = useQuery({ queryKey: ["mediciones-biofloc", loteId], queryFn: () => listMedicionesBiofloc(loteId) });
  const aplicacionesQuery = useQuery({ queryKey: ["aplicaciones-biofloc", loteId], queryFn: () => listAplicacionesBiofloc(loteId) });
  const [formErrorAplicacion, setFormErrorAplicacion] = useState<string | null>(null);
  const [formErrorMedicion, setFormErrorMedicion] = useState<string | null>(null);

  const tipos = tiposQuery.data ?? [];

  const form = useForm({
    defaultValues: {
      lote_id: loteId,
      tipo_aplicacion_id: 0,
      producto_id: "",
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      unidad: "",
      observaciones: "",
    },
  });

  useEffect(() => {
    if (tipos.length === 0) return;
    const primero = tipos[0]?.id ?? 0;
    const actual = form.getValues("tipo_aplicacion_id");
    if (actual === 0 && primero) {
      form.reset({
        ...form.getValues(),
        tipo_aplicacion_id: primero,
      });
    }
  }, [tiposQuery.data]);

  const formMedicion = useForm({
    defaultValues: {
      lote_id: loteId,
      fecha_hora: toDatetimeLocalValue(),
      volumen_sedimentable: "",
      unidad: medicionesQuery.data?.[0]?.unidad ?? "",
      relacion_cn: "",
      observaciones: "",
    },
  });

  const mutationAplicacion = useMutation({
    mutationFn: (data: AplicacionBioflocCreate) => createAplicacionBiofloc(data),
    onSuccess: async () => {
      setFormErrorAplicacion(null);
      await onSaved();
    },
    onError: (err) => setFormErrorAplicacion(apiErrorMessage(err)),
  });

  const mutationMedicion = useMutation({
    mutationFn: (data: MedicionBioflocCreate) => createMedicionBiofloc(data),
    onSuccess: async () => {
      setFormErrorMedicion(null);
      await onSaved();
    },
    onError: (err) => setFormErrorMedicion(apiErrorMessage(err)),
  });

  const productos = productosQuery.data ?? [];
  const historialMediciones = (medicionesQuery.data ?? []).slice(0, 5);
  const historialAplicaciones = (aplicacionesQuery.data ?? []).slice(0, 5);

  return (
    <Modal open={open} title="Registrar Biofloc" onClose={onClose}>
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            type="button"
            className={modo === "aplicacion" ? "bf-btn-primary !py-1.5 text-xs" : "bf-btn-secondary !py-1.5 text-xs"}
            onClick={() => setModo("aplicacion")}
          >
            Aplicación
          </button>
          <button
            type="button"
            className={modo === "medicion" ? "bf-btn-primary !py-1.5 text-xs" : "bf-btn-secondary !py-1.5 text-xs"}
            onClick={() => setModo("medicion")}
          >
            Medición
          </button>
        </div>

        {modo === "aplicacion" ? (
          <form
            className="space-y-3"
            onSubmit={form.handleSubmit((values) => {
              const fechaHora = withFechaHoraIso(values.fecha_hora, setFormErrorAplicacion);
              if (!fechaHora) return;
              const producto = values.producto_id.trim();
              const cantidad = values.cantidad.trim();
              mutationAplicacion.mutate({
                lote_id: loteId,
                tipo_aplicacion_id: Number(values.tipo_aplicacion_id),
                producto_id: producto === "" ? null : Number(producto),
                fecha_hora: fechaHora,
                cantidad: cantidad === "" ? null : Number(cantidad),
                unidad: values.unidad.trim() || null,
                observaciones: values.observaciones.trim() || null,
              });
            })}
          >
            {formErrorAplicacion ? <ErrorAlert message={formErrorAplicacion} /> : null}
            {tiposQuery.isLoading || productosQuery.isLoading ? <LoadingState label="Cargando catálogos…" /> : null}

            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />

            <Field label="Tipo de aplicación">
              <select className="bf-input" {...form.register("tipo_aplicacion_id", { valueAsNumber: true, required: true })}>
                {tipos.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Producto (opcional)">
              <select className="bf-input" {...form.register("producto_id")}>
                <option value="">Ninguno</option>
                {productos.map((row) => (
                  <option key={row.id} value={row.id}>
                    {etiquetaProducto(row.nombre, row.codigo)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Fecha y hora">
              <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
            </Field>

            <Field label="Cantidad (opcional)">
              <input type="number" step="any" min="0" className="bf-input" {...form.register("cantidad")} />
            </Field>

            <Field label="Unidad (opcional, texto del API)">
              <input className="bf-input" {...form.register("unidad")} />
            </Field>

            <Field label="Observaciones">
              <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
            </Field>

            <p className="text-xs text-[var(--bf-muted)]">
              Si se indica producto y cantidad, se aplica la lógica actual de inventario en backend.
            </p>

            <button
              type="submit"
              className="bf-btn-primary"
              disabled={mutationAplicacion.isPending || tipos.length === 0}
            >
              {mutationAplicacion.isPending ? "Guardando…" : "Registrar aplicación"}
            </button>
          </form>
        ) : null}

        {modo === "medicion" ? (
          <form
            className="space-y-3"
            onSubmit={formMedicion.handleSubmit((values) => {
              const fechaHora = withFechaHoraIso(values.fecha_hora, setFormErrorMedicion);
              if (!fechaHora) return;
              const cn = values.relacion_cn.trim();
              mutationMedicion.mutate({
                lote_id: loteId,
                fecha_hora: fechaHora,
                volumen_sedimentable: Number(values.volumen_sedimentable),
                unidad: values.unidad.trim() || "mL/L",
                relacion_cn: cn === "" ? null : Number(cn),
                observaciones: values.observaciones.trim() || null,
              });
            })}
          >
            {formErrorMedicion ? <ErrorAlert message={formErrorMedicion} /> : null}

            <input type="hidden" {...formMedicion.register("lote_id", { valueAsNumber: true })} />

            <Field label="Parámetro / indicador">
              <input className="bf-input" value="VOLUMEN_SEDIMENTABLE" readOnly />
            </Field>

            <Field label="Fecha y hora">
              <input type="datetime-local" className="bf-input" {...formMedicion.register("fecha_hora", { required: true })} />
            </Field>

            <Field label="Valor medido">
              <input
                type="number"
                step="any"
                min="0"
                className="bf-input"
                {...formMedicion.register("volumen_sedimentable", { valueAsNumber: true, required: true })}
              />
            </Field>

            <Field label="Unidad">
              <input className="bf-input" {...formMedicion.register("unidad")} />
            </Field>

            <Field label="Relación C/N (opcional)">
              <input type="number" step="any" min="0" className="bf-input" {...formMedicion.register("relacion_cn")} />
            </Field>

            <Field label="Observaciones">
              <textarea className="bf-input min-h-20" {...formMedicion.register("observaciones")} />
            </Field>

            <button type="submit" className="bf-btn-primary" disabled={mutationMedicion.isPending}>
              {mutationMedicion.isPending ? "Guardando…" : "Registrar medición"}
            </button>
          </form>
        ) : null}

        <div className="grid gap-3 border-t border-[var(--bf-border)] pt-3 sm:grid-cols-2">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Aplicaciones recientes</h3>
            {aplicacionesQuery.isLoading ? <p className="mt-2 text-xs text-[var(--bf-muted)]">Cargando…</p> : null}
            {!aplicacionesQuery.isLoading && historialAplicaciones.length === 0 ? (
              <p className="mt-2 text-xs text-[var(--bf-muted)]">N/D — Sin aplicaciones</p>
            ) : null}
            <div className="mt-2 space-y-2">
              {historialAplicaciones.map((row) => (
                <div key={row.id} className="rounded-lg border border-[var(--bf-border)] p-2 text-xs">
                  <p className="font-medium text-[var(--bf-ink)]">{formatDate(row.fecha_hora)}</p>
                  <p className="text-[var(--bf-muted)]">
                    {tipos.find((t) => t.id === row.tipo_aplicacion_id)?.nombre ?? `Tipo #${row.tipo_aplicacion_id}`}
                  </p>
                  <p className="text-[var(--bf-muted)]">
                    {row.cantidad == null ? "—" : `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })} ${row.unidad ?? ""}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Mediciones recientes</h3>
            {medicionesQuery.isLoading ? <p className="mt-2 text-xs text-[var(--bf-muted)]">Cargando…</p> : null}
            {!medicionesQuery.isLoading && historialMediciones.length === 0 ? (
              <p className="mt-2 text-xs text-[var(--bf-muted)]">N/D — Sin mediciones</p>
            ) : null}
            <div className="mt-2 space-y-2">
              {historialMediciones.map((row) => (
                <div key={row.id} className="rounded-lg border border-[var(--bf-border)] p-2 text-xs">
                  <p className="font-medium text-[var(--bf-ink)]">{formatDate(row.fecha_hora)}</p>
                  <p className="text-[var(--bf-muted)]">Sólidos sedimentables</p>
                  <p className="text-[var(--bf-muted)]">
                    {formatNumber(row.volumen_sedimentable, { maximumFractionDigits: 3 })} {row.unidad}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}

function CosechaModal({
  open,
  onClose,
  onSaved,
  lote,
  estanque,
  ind,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
  lote: Lote;
  estanque: { codigo: string } | null;
  ind: AnalisisIndicadores | undefined;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const [step, setStep] = useState<"form" | "confirm">("form");
  const [pending, setPending] = useState<CosechaCreate | null>(null);
  const disponible = ind?.poblacion_estimada ?? null;

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
      setFormError(null);
      await onSaved();
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  const restantesConfirm =
    pending && disponible != null ? disponible - pending.cantidad_peces : null;

  return (
    <Modal
      open={open}
      title="Registrar cosecha"
      onClose={() => {
        setStep("form");
        setPending(null);
        onClose();
      }}
    >
      {formError ? <ErrorAlert message={formError} /> : null}

      {step === "form" ? (
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
            const promedioTxt = values.peso_promedio_g.trim();
            const pesoPromedio = promedioTxt === "" ? null : Number(promedioTxt);
            const data: CosechaCreate = {
              lote_id: lote.id,
              fecha_hora: fechaHora,
              cantidad_peces: cantidadPeces,
              peso_total_kg: pesoTotalKg,
              peso_promedio_g: pesoPromedio,
              observaciones: values.observaciones.trim() || null,
            };
            setFormError(null);
            setPending(data);
            setStep("confirm");
          })}
        >
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

          <Field label="Cantidad de peces cosechados">
            <input type="number" min="1" step="1" className="bf-input" {...form.register("cantidad_peces", { required: true })} />
          </Field>

          <Field label="Peso total cosechado (kg)">
            <input type="number" step="any" min="0.001" className="bf-input" {...form.register("peso_total_kg", { required: true })} />
          </Field>

          <Field label="Peso promedio por pez (opcional, g)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("peso_promedio_g")} />
          </Field>

          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>

          <button type="submit" className="bf-btn-primary !mt-2" disabled={mutation.isPending}>
            Revisar cosecha
          </button>
        </form>
      ) : null}

      {step === "confirm" && pending ? (
        <div className="space-y-3">
          {restantesConfirm != null ? (
            <p className="text-sm font-medium text-[var(--bf-ink)]">{mensajeRestantesCosecha(restantesConfirm)}</p>
          ) : null}
          {restantesConfirm === 0 ? (
            <p className="text-sm text-[var(--bf-muted)]">
              El lote pasará al estado FINALIZADO. El historial permanecerá disponible.
            </p>
          ) : (
            <p className="text-sm text-[var(--bf-muted)]">
              Cosecha parcial: el lote permanece ACTIVO.
            </p>
          )}
          <dl className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Lote</dt>
              <dd>{lote.codigo}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Estanque</dt>
              <dd>{estanque?.codigo ?? "N/D"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Población disponible</dt>
              <dd>{disponible == null ? "N/D" : `${formatNumber(disponible)} peces`}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Cantidad a cosechar</dt>
              <dd>{formatNumber(pending.cantidad_peces)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Peso total</dt>
              <dd>{formatNumber(pending.peso_total_kg, { maximumFractionDigits: 3 })} kg</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--bf-muted)]">Peso promedio actual del lote</dt>
              <dd>{ind?.peso_promedio_g == null ? "N/D" : `${nd(ind.peso_promedio_g, 2)} g`}</dd>
            </div>
          </dl>

          <div className="mt-4 flex flex-wrap gap-2 justify-end">
            <button
              type="button"
              className="bf-btn-secondary"
              onClick={() => {
                setStep("form");
                setPending(null);
              }}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="bf-btn-primary"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(pending)}
            >
              {mutation.isPending ? "Guardando…" : "Confirmar cosecha"}
            </button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
