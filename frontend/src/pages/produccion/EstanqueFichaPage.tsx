import { Link, useParams, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useState, type ReactNode } from "react";
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
  createLote,
  getEstanque,
  getLote,
  getCostosLote,
  listLotes,
  registrarSiembra,
  listEspecies,
  listEtapasProductivas,
  listEstadosLote,
} from "../../api/production";
import {
  createAlimentacion,
  createAplicacionBiofloc,
  createMedicionBiofloc,
  createMedicionAgua,
  createAcondicionamientoBioflocEstanque,
  listAplicacionesBiofloc,
  listAcondicionamientosBioflocEstanque,
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
import { listCategoriasInventario, listProductos } from "../../api/inventory";
import { PATH_COMPARACION } from "./fichaPaths";
import { LoteFichaWorkspace, parseLoteFichaTab, type LoteFichaTabId } from "./LoteFichaPage";
import type { Lote, LoteCreate, SiembraLoteCreate } from "../../types/production";
import type { BiometriaCreate, CosechaCreate, MortalidadCreate } from "../../types/production";
import type {
  AlimentacionCreate,
  AplicacionBioflocCreate,
  Producto,
  MedicionAguaCreate,
  MedicionBioflocCreate,
  AcondicionamientoBioflocEstanqueCreate,
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
  const loteActivo = lotes.find((item) => item.estado.nombre === "ACTIVO");
  const lotePreparacion = lotes.find((item) => item.estado.nombre === "PLANIFICADO");
  const hayLoteActivo = Boolean(loteActivo);
  const loteQuery = useQuery({
    queryKey: ["lote", loteResumen?.id],
    queryFn: () => getLote(loteResumen!.id),
    enabled: Boolean(loteResumen?.id),
  });
  const lote = loteQuery.data ?? loteResumen;
  const costosQuery = useQuery({
    queryKey: ["costos-lote", lote?.id],
    queryFn: () => getCostosLote(lote!.id),
    enabled: Boolean(lote?.id),
  });
  const analisisQuery = useQuery({
    queryKey: ["analisis-lote", lote?.id, "", ""],
    queryFn: () => getAnalisisLote(lote!.id),
    enabled: Boolean(lote?.id && lote?.estado.nombre !== "PLANIFICADO"),
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
    await queryClient.invalidateQueries({ queryKey: ["costos-lote", lote.id] });
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
  const proyeccion = lote && lote.estado.nombre !== "PLANIFICADO" && ind
    ? proyectarCosecha({
        fechaSiembra: lote.fecha_siembra,
        diasCultivo: ind.dias_cultivo,
        pesoActualG: num(ind.peso_promedio_g),
        gananciaDiariaG: num(ind.ganancia_diaria_g),
        poblacion: ind.poblacion_estimada,
      })
    : lote && lote.estado.nombre !== "PLANIFICADO"
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

        {!hayLoteActivo ? (
          lotePreparacion ? (
            <>
              <SiembraLotePanel
                lote={lotePreparacion}
                puedeRegistrar={can(user?.rol, "crearLote")}
                onSown={async () => {
                  await queryClient.invalidateQueries({ queryKey: ["lotes", estanqueId] });
                  await queryClient.invalidateQueries({ queryKey: ["lote", lotePreparacion.id] });
                  await queryClient.invalidateQueries({ queryKey: ["stock"] });
                  await queryClient.invalidateQueries({ queryKey: ["productos-stock"] });
                }}
              />
              <AcondicionamientoBioflocEstanquePanel
                loteId={lotePreparacion.id}
                puedeRegistrar={can(user?.rol, "registrarBiofloc")}
                puedeMedirAgua={can(user?.rol, "registrarAgua")}
                puedeMedirBiofloc={can(user?.rol, "registrarBiofloc")}
                onMeasureWater={() => setModalAccion("agua")}
                onMeasureBiofloc={() => setModalAccion("biofloc")}
              />
              {modalAccion === "agua" ? (
                <AguaModal
                  loteId={lotePreparacion.id}
                  open
                  onClose={() => setModalAccion(null)}
                  onSaved={async () => {
                    await queryClient.invalidateQueries({ queryKey: ["mediciones-agua", lotePreparacion.id] });
                    setModalAccion(null);
                  }}
                />
              ) : null}
              {modalAccion === "biofloc" ? (
                <BioflocModal
                  loteId={lotePreparacion.id}
                  open
                  onClose={() => setModalAccion(null)}
                  onSaved={async () => {
                    await queryClient.invalidateQueries({ queryKey: ["mediciones-biofloc", lotePreparacion.id] });
                    setModalAccion(null);
                  }}
                />
              ) : null}
            </>
          ) : (
            <CrearCicloPreparacionPanel
              estanque={estanque}
              puedeRegistrar={can(user?.rol, "crearLote")}
              onCreated={(nuevoLote) => {
                queryClient.invalidateQueries({ queryKey: ["lotes", estanqueId] });
                setLote(nuevoLote.id);
              }}
            />
          )
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
            <div className="mx-6 mb-5 rounded-2xl border border-[var(--bf-border)] bg-[var(--bf-chip)] p-4">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Costo ejecutado del lote</p>
                  <p className="mt-1 text-2xl font-extrabold text-[var(--bf-ink)]">$ {nd(costosQuery.data?.costo_directo_lote, 2)}</p>
                  <p className="mt-1 text-xs text-gray-500">Solo consumos y aplicaciones asignados a este ciclo; las compras de inventario no se cargan aquí.</p>
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-4">
                  <div><span className="text-gray-500">Alevinos</span><div className="font-semibold">$ {nd(costosQuery.data?.alevinos, 2)}</div></div>
                  <div><span className="text-gray-500">Alimento</span><div className="font-semibold">$ {nd(costosQuery.data?.alimento, 2)}</div></div>
                  <div><span className="text-gray-500">Biofloc</span><div className="font-semibold">$ {nd(Math.max(0, Number(costosQuery.data?.biofloc_insumos ?? 0)), 2)}</div></div>
                  <div><span className="text-gray-500">Costo/kg</span><div className="font-semibold">{costosQuery.data?.costo_por_kg == null ? "N/D" : "$ " + nd(costosQuery.data.costo_por_kg, 2)}</div></div>
                </div>
              </div>
            </div>

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
            {productos.map((row: Producto) => (
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
    if (actual === 0 && primero) form.setValue("parametro_id", primero);
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
    <Modal open={open} title="Medir calidad de agua — Lote" onClose={onClose}>
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
        <Field label="Parámetro">
          <select className="bf-input" {...form.register("parametro_id", { valueAsNumber: true, required: true })}>
            {parametros.map((row) => <option key={row.id} value={row.id}>{row.nombre} ({row.unidad})</option>)}
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
          {mutation.isPending ? "Guardando…" : "Registrar medición"}
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
  const [modo, setModo] = useState<"aplicacion" | "medicion">("medicion");
  const tiposQuery = useQuery({ queryKey: ["tipos-aplicacion-biofloc"], queryFn: () => listTiposAplicacionBiofloc(true) });
  const productosQuery = useQuery({ queryKey: ["productos-activos"], queryFn: listProductosActivos });
  const medicionesQuery = useQuery({
    queryKey: ["mediciones-biofloc", loteId],
    queryFn: () => listMedicionesBiofloc(loteId),
  });
  const aplicacionesQuery = useQuery({
    queryKey: ["aplicaciones-biofloc", loteId],
    queryFn: () => listAplicacionesBiofloc(loteId),
    enabled: Boolean(loteId),
  });
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
    if (form.getValues("tipo_aplicacion_id") === 0 && primero) form.setValue("tipo_aplicacion_id", primero);
  }, [tiposQuery.data]);

  const formMedicion = useForm({
    defaultValues: {
      fecha_hora: toDatetimeLocalValue(),
      volumen_sedimentable: "",
      unidad: "mL/L",
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
  const tipoAplicacionId = form.watch("tipo_aplicacion_id");
  const tipoAplicacion = tipos.find((row) => row.id === Number(tipoAplicacionId));
  const productosBiofloc = useMemo(() => {
    const tipo = (tipoAplicacion?.nombre ?? "").toUpperCase();
    const patrones: RegExp[] = tipo.includes("PROBIOTICO") ? [/probi[oó]tico/i]
      : tipo.includes("FUENTE_CARBONO") ? [/melaza/i]
      : tipo.includes("CORRECTIVO") ? [/sal\s*marina/i, /bicarbonato/i] : [];
    return productos.filter((row) => patrones.some((patron) => patron.test(row.nombre) || patron.test(row.codigo)));
  }, [productos, tipoAplicacion?.nombre]);

  const historialMediciones = (medicionesQuery.data ?? []).slice(0, 5);
  const historialAplicaciones = (aplicacionesQuery.data ?? []).slice(0, 5);

  return (
    <Modal open={open} title="Registrar Biofloc — Lote" onClose={onClose}>
      <div className="space-y-4">
        <div className="flex gap-2">
            <button type="button" className={modo === "aplicacion" ? "bf-btn-primary !py-1.5 text-xs" : "bf-btn-secondary !py-1.5 text-xs"} onClick={() => setModo("aplicacion")}>Aplicación</button>
            <button type="button" className={modo === "medicion" ? "bf-btn-primary !py-1.5 text-xs" : "bf-btn-secondary !py-1.5 text-xs"} onClick={() => setModo("medicion")}>Medición</button>
        </div>

        {modo === "aplicacion" ? (
          <form className="space-y-3" onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormErrorAplicacion);
            if (!fechaHora) return;
            const producto = values.producto_id.trim();
            const cantidad = values.cantidad.trim();
            if (cantidad !== "" && Number(cantidad) > 0 && producto === "") {
              setFormErrorAplicacion("Seleccione un insumo Biofloc cuando registre una cantidad mayor que 0.");
              return;
            }
            mutationAplicacion.mutate({
              lote_id: loteId!,
              tipo_aplicacion_id: Number(values.tipo_aplicacion_id),
              producto_id: producto === "" ? null : Number(producto),
              fecha_hora: fechaHora,
              cantidad: cantidad === "" ? null : Number(cantidad),
              unidad: values.unidad.trim() || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}>
            {formErrorAplicacion ? <ErrorAlert message={formErrorAplicacion} /> : null}
            {tiposQuery.isLoading || productosQuery.isLoading ? <LoadingState label="Cargando catálogos…" /> : null}
            <Field label="Tipo de aplicación">
              <select className="bf-input" {...form.register("tipo_aplicacion_id", { valueAsNumber: true, required: true, onChange: () => form.setValue("producto_id", "") })}>
                {tipos.map((row) => <option key={row.id} value={row.id}>{row.nombre}</option>)}
              </select>
            </Field>
            <Field label="Producto">
              <select className="bf-input" disabled={productosBiofloc.length === 0} {...form.register("producto_id")}>
                <option value="">{productosBiofloc.length ? "Seleccione un insumo" : "No requiere producto"}</option>
                {productosBiofloc.map((row) => <option key={row.id} value={row.id}>{etiquetaProducto(row.nombre, row.codigo)}</option>)}
              </select>
            </Field>
            <Field label="Fecha y hora">
              <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
            </Field>
            <Field label="Cantidad (opcional)">
              <input type="number" step="any" min="0" className="bf-input" {...form.register("cantidad")} />
            </Field>
            <Field label="Unidad (opcional)">
              <input className="bf-input" {...form.register("unidad")} />
            </Field>
            <Field label="Observaciones">
              <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
            </Field>
            <p className="text-xs text-[var(--bf-muted)]">Los consumos con cantidad mayor que 0 generan automáticamente una salida de inventario y afectan el costo de producción.</p>
            <button type="submit" className="bf-btn-primary" disabled={mutationAplicacion.isPending || tipos.length === 0}>{mutationAplicacion.isPending ? "Guardando…" : "Registrar aplicación"}</button>
          </form>
        ) : null}

        {modo === "medicion" ? (
          <form className="space-y-3" onSubmit={formMedicion.handleSubmit((values) => {
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
          })}>
            {formErrorMedicion ? <ErrorAlert message={formErrorMedicion} /> : null}
            <Field label="Parámetro / indicador">
              <input className="bf-input" value="VOLUMEN_SEDIMENTABLE" readOnly />
            </Field>
            <Field label="Fecha y hora">
              <input type="datetime-local" className="bf-input" {...formMedicion.register("fecha_hora", { required: true })} />
            </Field>
            <Field label="Volumen sedimentable">
              <input type="number" step="any" min="0" className="bf-input" {...formMedicion.register("volumen_sedimentable", { valueAsNumber: true, required: true })} />
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
            <button type="submit" className="bf-btn-primary" disabled={mutationMedicion.isPending}>{mutationMedicion.isPending ? "Guardando…" : "Registrar medición"}</button>
          </form>
        ) : null}

        <div className="grid gap-3 border-t border-[var(--bf-border)] pt-3 sm:grid-cols-2">
          <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Aplicaciones recientes</h3>
              {aplicacionesQuery.isLoading ? <p className="mt-2 text-xs text-[var(--bf-muted)]">Cargando…</p> : null}
              {!aplicacionesQuery.isLoading && historialAplicaciones.length === 0 ? <p className="mt-2 text-xs text-[var(--bf-muted)]">N/D — Sin aplicaciones</p> : null}
              <div className="mt-2 space-y-2">
                {historialAplicaciones.map((row) => (
                  <div key={row.id} className="rounded-lg border border-[var(--bf-border)] p-2 text-xs">
                    <p className="font-medium text-[var(--bf-ink)]">{formatDate(row.fecha_hora)}</p>
                    <p className="text-[var(--bf-muted)]">{tipos.find((t) => t.id === row.tipo_aplicacion_id)?.nombre ?? `Tipo #${row.tipo_aplicacion_id}`}</p>
                    <p className="text-[var(--bf-muted)]">{row.cantidad == null ? "—" : `${formatNumber(row.cantidad, { maximumFractionDigits: 3 })} ${row.unidad ?? ""}`}</p>
                  </div>
                ))}
              </div>
            </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">Mediciones recientes</h3>
            {medicionesQuery.isLoading ? <p className="mt-2 text-xs text-[var(--bf-muted)]">Cargando…</p> : null}
            {!medicionesQuery.isLoading && historialMediciones.length === 0 ? <p className="mt-2 text-xs text-[var(--bf-muted)]">N/D — Sin mediciones</p> : null}
            <div className="mt-2 space-y-2">
              {historialMediciones.map((row) => (
                <div key={row.id} className="rounded-lg border border-[var(--bf-border)] p-2 text-xs">
                  <p className="font-medium text-[var(--bf-ink)]">{formatDate(row.fecha_hora)}</p>
                  <p className="text-[var(--bf-muted)]">Sólidos sedimentables</p>
                  <p className="text-[var(--bf-muted)]">{formatNumber(row.volumen_sedimentable, { maximumFractionDigits: 3 })} {row.unidad}</p>
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

function CrearCicloPreparacionPanel({
  estanque,
  puedeRegistrar,
  onCreated,
}: {
  estanque: { id: number; codigo: string; nombre: string };
  puedeRegistrar: boolean;
  onCreated: (lote: Lote) => void;
}) {
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const especiesQuery = useQuery({ queryKey: ["especies", "ciclo-preparacion"], queryFn: () => listEspecies(true) });
  const etapasQuery = useQuery({ queryKey: ["etapas-productivas", "ciclo-preparacion"], queryFn: () => listEtapasProductivas(true) });
  const estadosQuery = useQuery({ queryKey: ["estados-lote", "ciclo-preparacion"], queryFn: () => listEstadosLote(true) });
  const especieInicial = especiesQuery.data?.[0]?.id ?? 0;
  const etapaInicial = etapasQuery.data?.find((row) => row.nombre.toUpperCase() === "ALEVINAJE") ?? etapasQuery.data?.[0];
  const estadoPlanificado = estadosQuery.data?.find((row) => row.nombre.toUpperCase() === "PLANIFICADO");
  const [fechaSiembra, setFechaSiembra] = useState("");
  const [cantidad, setCantidad] = useState("1100");
  const [especieId, setEspecieId] = useState(0);
  const [observaciones, setObservaciones] = useState("");

  useEffect(() => {
    if (!especieId && especieInicial) setEspecieId(especieInicial);
  }, [especieInicial, especieId]);

  const mutation = useMutation({
    mutationFn: (data: LoteCreate) => createLote(data),
    onSuccess: (lote) => {
      setOpen(false);
      setFormError(null);
      onCreated(lote);
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  const fechaMinima = new Date().toISOString().slice(0, 10);
  const codigo = fechaSiembra ? "LT-" + estanque.codigo + "-" + fechaSiembra.replaceAll("-", "") : "LT-" + estanque.codigo + "-NUEVO";

  return (
    <div className="border-t border-[var(--bf-border)] px-6 pb-8 pt-6">
      <div className="rounded-2xl border border-[var(--bf-border)] bg-[var(--bf-chip)] p-5">
        <FichaLabel>Nuevo ciclo</FichaLabel>
        <h2 className="mt-1 text-2xl font-bold text-[var(--bf-ink)]">Preparar estanque para una siembra</h2>
        <p className="mt-2 max-w-3xl text-sm text-[var(--bf-muted)]">
          Primero se crea el lote planificado. Desde ese momento, el acondicionamiento y las mediciones de agua/Biofloc quedan asociados a ese ciclo.
        </p>
        <div className="mt-4 flex justify-end">
          {puedeRegistrar ? <button type="button" className="bf-btn-primary" onClick={() => { setFormError(null); setOpen(true); }}>Crear lote de preparación</button> : null}
        </div>
      </div>

      <Modal open={open} title="Crear lote — Preparación de siembra" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          if (!especieId || !etapaInicial?.id || !estadoPlanificado?.id) {
            setFormError("No se pudieron cargar los catálogos necesarios para crear el ciclo.");
            return;
          }
          if (!fechaSiembra) { setFormError("Indique la fecha prevista de siembra."); return; }
          if (Number(cantidad) <= 0) { setFormError("La cantidad prevista debe ser mayor que 0."); return; }
          mutation.mutate({
            codigo,
            estanque_id: estanque.id,
            especie_id: especieId,
            etapa_productiva_id: etapaInicial.id,
            estado_id: estadoPlanificado.id,
            fecha_siembra: fechaSiembra,
            cantidad_prevista: Number(cantidad),
            peso_inicial_promedio_g: null,
            observaciones: observaciones.trim() || "Ciclo creado para preparación y acondicionamiento Biofloc previo a la siembra.",
          });
        }}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Especie">
            <select className="bf-input" value={especieId} onChange={(e) => setEspecieId(Number(e.target.value))}>
              {(especiesQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.nombre_comun}</option>)}
            </select>
          </Field>
          <Field label="Etapa inicial">
            <input className="bf-input" value={etapaInicial?.nombre ?? "Alevinaje"} readOnly />
          </Field>
          <Field label="Fecha prevista de siembra">
            <input type="date" min={fechaMinima} className="bf-input" value={fechaSiembra} onChange={(e) => setFechaSiembra(e.target.value)} required />
          </Field>
          <Field label="Cantidad prevista de peces">
            <input type="number" min="1" step="1" className="bf-input" value={cantidad} onChange={(e) => setCantidad(e.target.value)} required />
          </Field>
          <Field label="Código del ciclo">
            <input className="bf-input" value={codigo} readOnly />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">El lote quedará en estado PLANIFICADO. Todavía no representa peces sembrados; representa el ciclo que se está preparando.</p>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || !puedeRegistrar || especiesQuery.isLoading || etapasQuery.isLoading || estadosQuery.isLoading}>
            {mutation.isPending ? "Creando…" : "Crear ciclo de preparación"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function SiembraLotePanel({ lote, puedeRegistrar, onSown }: { lote: Lote; puedeRegistrar: boolean; onSown: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const categoriasQuery = useQuery({ queryKey: ["categorias-inventario"], queryFn: () => listCategoriasInventario(true) });
  const categoriaAlevinos = categoriasQuery.data?.find((row) => row.nombre === "ALEVINOS");
  const productosQuery = useQuery({
    queryKey: ["productos-alevinos", categoriaAlevinos?.id],
    queryFn: () => listProductos({ soloActivos: true, categoriaId: categoriaAlevinos!.id }),
    enabled: Boolean(categoriaAlevinos?.id),
  });
  const mutation = useMutation({
    mutationFn: (data: SiembraLoteCreate) => registrarSiembra(lote.id, data),
    onSuccess: async (resp) => {
      setOpen(false);
      setFormError(null);
      setSuccess("Siembra registrada: " + formatNumber(resp.cantidad_sembrada) + " peces · costo imputado " + formatNumber(resp.costo_total, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
      await onSown();
      setTimeout(() => setSuccess(null), 7000);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const form = useForm({
    defaultValues: { producto_id: "", cantidad: String(lote.cantidad_prevista), fecha_hora: toDatetimeLocalValue(), peso: "", observaciones: "" },
  });
  return (
    <div className="border-t border-[var(--bf-border)] px-6 pb-5 pt-5">
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <FichaLabel>Acción pendiente</FichaLabel>
            <h2 className="mt-1 text-xl font-bold text-[var(--bf-ink)]">Registrar siembra</h2>
            <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">La compra de alevinos solo aumenta el inventario. El costo del lote nace aquí, cuando los peces realmente se consumen para la siembra.</p>
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-amber-700">PLANIFICADO</span>
        </div>
        {success ? <div className="mt-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">{success}</div> : null}
        {puedeRegistrar ? (
          <div className="mt-4 flex justify-end">
            <button type="button" className="bf-btn-primary" onClick={() => { setFormError(null); form.reset({ producto_id: "", cantidad: String(lote.cantidad_sembrada), fecha_hora: toDatetimeLocalValue(), peso: "", observaciones: "" }); setOpen(true); }}>
              Sembrar lote
            </button>
          </div>
        ) : null}
      </div>
      <Modal open={open} title={"Registrar siembra · " + lote.codigo} onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={form.handleSubmit((values) => {
          const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
          if (!fechaHora) return;
          const cantidad = Number(values.cantidad);
          const peso = values.peso.trim();
          if (!values.producto_id) { setFormError("Seleccione el producto de alevinos."); return; }
          if (!Number.isInteger(cantidad) || cantidad <= 0) { setFormError("La cantidad sembrada debe ser un número entero mayor que 0."); return; }
          mutation.mutate({ producto_id: Number(values.producto_id), cantidad, fecha_hora: fechaHora, peso_inicial_promedio_g: peso === "" ? null : Number(peso), observaciones: values.observaciones.trim() || null });
        })}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Producto de alevinos">
            <select className="bf-input" {...form.register("producto_id")} disabled={!productosQuery.data?.length}>
              <option value="">{productosQuery.isLoading ? "Cargando alevinos…" : productosQuery.data?.length ? "Seleccione el producto" : "No hay productos ALEVINOS activos"}</option>
              {(productosQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{etiquetaProducto(row.nombre, row.codigo)}</option>)}
            </select>
          </Field>
          <Field label={"Cantidad real sembrada (prevista: " + formatNumber(lote.cantidad_prevista) + ")"}>
            <input type="number" min="1" step="1" className="bf-input" {...form.register("cantidad")} />
          </Field>
          <Field label="Fecha y hora de siembra">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Peso inicial promedio (g, opcional)">
            <input type="number" min="0" step="any" className="bf-input" {...form.register("peso")} />
          </Field>
          <Field label="Observaciones"><textarea className="bf-input min-h-20" {...form.register("observaciones")} /></Field>
          <p className="text-xs text-[var(--bf-muted)]">La operación descuenta los alevinos del inventario y toma automáticamente su costo promedio histórico. La compra original no se suma al lote.</p>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || !productosQuery.data?.length}>
            {mutation.isPending ? "Registrando…" : "Confirmar siembra"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function AcondicionamientoBioflocEstanquePanel({
  loteId,
  puedeRegistrar,
  puedeMedirAgua,
  puedeMedirBiofloc,
  onMeasureWater,
  onMeasureBiofloc,
}: {
  loteId: number;
  puedeRegistrar: boolean;
  puedeMedirAgua: boolean;
  puedeMedirBiofloc: boolean;
  onMeasureWater: () => void;
  onMeasureBiofloc: () => void;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [stockMsg, setStockMsg] = useState<string | null>(null);
  const tiposQuery = useQuery({
    queryKey: ["tipos-aplicacion-biofloc"],
    queryFn: () => listTiposAplicacionBiofloc(true),
  });
  const productosQuery = useQuery({
    queryKey: ["productos-activos"],
    queryFn: listProductosActivos,
  });
  const query = useQuery({
    queryKey: ["acondicionamientos-biofloc-lote", loteId],
    queryFn: () => listAcondicionamientosBioflocEstanque(loteId),
  });
  const loteQuery = useQuery({ queryKey: ["lote", loteId], queryFn: () => getLote(loteId) });
  const lote = loteQuery.data;
  const tipos = useMemo(
    () => new Map((tiposQuery.data ?? []).map((row) => [row.id, row])),
    [tiposQuery.data],
  );
  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((row) => [row.id, row])),
    [productosQuery.data],
  );
  const productosBiofloc = useMemo(
    () => (productosQuery.data ?? []).filter((row) =>
      /^BF-/i.test(row.codigo) ||
      /melaza|probiótico|bicarbonato|sal marina/i.test(row.nombre),
    ),
    [productosQuery.data],
  );
  const puedeCrear = puedeRegistrar && Boolean(tiposQuery.data?.length) && Boolean(productosQuery.data);

  const form = useForm({
    defaultValues: {
      tipo_aplicacion_id: tiposQuery.data?.[0]?.id ?? 0,
      producto_id: "",
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      unidad: "kg",
      aireacion_activa: true,
      observaciones: "",
    },
  });

  useEffect(() => {
    if (tiposQuery.data?.length && form.getValues("tipo_aplicacion_id") === 0) {
      form.setValue("tipo_aplicacion_id", tiposQuery.data[0].id);
    }
  }, [tiposQuery.data]);

  const tipoId = form.watch("tipo_aplicacion_id");
  const tipo = tipos.get(Number(tipoId));
  const productosFiltrados = useMemo(() => {
    const nombre = (tipo?.nombre ?? "").toUpperCase();
    if (nombre.includes("PROBIOTICO")) return productosBiofloc.filter((p) => /probi[oó]tico/i.test(p.nombre) || /PROBIOTICO/i.test(p.codigo));
    if (nombre.includes("FUENTE_CARBONO")) return productosBiofloc.filter((p) => /melaza/i.test(p.nombre) || /MELAZA/i.test(p.codigo));
    if (nombre.includes("CORRECTIVO")) return productosBiofloc.filter((p) => /bicarbonato|sal marina/i.test(p.nombre) || /BICARBONATO|SAL-MARINA/i.test(p.codigo));
    return productosBiofloc;
  }, [tipo?.nombre, productosBiofloc]);

  const mutation = useMutation({
    mutationFn: (data: AcondicionamientoBioflocEstanqueCreate) => createAcondicionamientoBioflocEstanque(data),
    onSuccess: async (resp) => {
      setOpen(false);
      if (resp.stock_restante != null) {
        setStockMsg(`Inventario actualizado: ${resp.stock_restante.toFixed(2)} disponibles`);
        setTimeout(() => setStockMsg(null), 6000);
      }
      await queryClient.invalidateQueries({ queryKey: ["acondicionamientos-biofloc-lote", loteId] });
      await queryClient.invalidateQueries({ queryKey: ["stock"] });
      await queryClient.invalidateQueries({ queryKey: ["productos-stock"] });
      form.reset({
        tipo_aplicacion_id: tiposQuery.data?.[0]?.id ?? 0,
        producto_id: "",
        fecha_hora: toDatetimeLocalValue(),
        cantidad: "",
        unidad: "kg",
        aireacion_activa: true,
        observaciones: "",
      });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });

  return (
    <div className="border-t border-[var(--bf-border)] px-6 pb-8 pt-6">
      <div className="rounded-2xl border border-[var(--bf-border)] bg-[var(--bf-chip)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <FichaLabel>Preparación de siembra</FichaLabel>
            <h2 className="mt-1 text-2xl font-bold text-[var(--bf-ink)]">Acondicionamiento Biofloc</h2>
            <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
              Este estanque no tiene lote activo. Aquí se prepara el sistema antes de sembrar los alevinos.
              La aplicación debe quedar dentro de los 7 días previos a la siembra del lote.
            </p>
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-[var(--bf-accent)]">PRE-SIEMBRA</span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl bg-white p-3"><p className="text-xs text-[var(--bf-muted)]">Especie</p><p className="mt-1 font-semibold">{lote?.especie.nombre_comun ?? "—"}</p></div>
          <div className="rounded-xl bg-white p-3"><p className="text-xs text-[var(--bf-muted)]">Siembra prevista</p><p className="mt-1 font-semibold">{lote?.fecha_siembra ? formatDate(lote.fecha_siembra) : "—"}</p></div>
          <div className="rounded-xl bg-white p-3"><p className="text-xs text-[var(--bf-muted)]">Peces previstos</p><p className="mt-1 font-semibold">{lote?.cantidad_sembrada ? formatNumber(lote.cantidad_sembrada) : "—"}</p></div>
          <div className="rounded-xl bg-white p-3"><p className="text-xs text-[var(--bf-muted)]">Aplicaciones</p><p className="mt-1 font-semibold">{query.data?.length ?? 0}</p></div>
        </div>
        {stockMsg ? <div className="mt-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">{stockMsg}</div> : null}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          {puedeMedirAgua ? (
            <button type="button" className="bf-btn-secondary" onClick={onMeasureWater}>
              Medir agua
            </button>
          ) : null}
          {puedeMedirBiofloc ? (
            <button type="button" className="bf-btn-secondary" onClick={onMeasureBiofloc}>
              Medir Biofloc
            </button>
          ) : null}
          {puedeCrear ? (
            <button type="button" className="bf-btn-primary" onClick={() => { setFormError(null); setOpen(true); }}>
              Acondicionar Biofloc
            </button>
          ) : null}
        </div>
        {query.data?.length ? (
          <div className="mt-5 overflow-x-auto rounded-xl bg-white">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--bf-border)] text-xs text-[var(--bf-muted)]">
                  <th className="px-4 py-3 font-semibold">Fecha</th>
                  <th className="px-4 py-3 font-semibold">Tipo</th>
                  <th className="px-4 py-3 font-semibold">Insumo</th>
                  <th className="px-4 py-3 font-semibold">Cantidad</th>
                  <th className="px-4 py-3 font-semibold">Aireación</th>
                </tr>
              </thead>
              <tbody>
                {(query.data ?? []).map((row) => (
                  <tr key={row.id} className="border-b border-[var(--bf-border)] last:border-b-0">
                    <td className="px-4 py-3">{formatDate(row.fecha_hora)}</td>
                    <td className="px-4 py-3">{tipos.get(row.tipo_aplicacion_id)?.nombre ?? `#${row.tipo_aplicacion_id}`}</td>
                    <td className="px-4 py-3">{row.producto_id ? (productos.get(row.producto_id)?.nombre ?? `#${row.producto_id}`) : "—"}</td>
                    <td className="px-4 py-3">
                      {row.cantidad == null
                        ? "—"
                        : `${formatNumber(row.cantidad, { maximumFractionDigits: 4 })} ${row.unidad ?? ""}`}
                    </td>
                    <td className="px-4 py-3">{row.aireacion_activa ? "Activa" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <Modal open={open} title="Acondicionar Biofloc — Estanque" onClose={() => setOpen(false)}>
        <form className="space-y-3" onSubmit={form.handleSubmit((values) => {
          const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
          if (!fechaHora) return;
          const cantidad = values.cantidad.trim();
          const producto = values.producto_id.trim();
          if (cantidad !== "" && Number(cantidad) > 0 && !producto) {
            setFormError("Seleccione el insumo cuando registre una cantidad mayor que 0.");
            return;
          }
          mutation.mutate({
            lote_id: loteId,
            tipo_aplicacion_id: Number(values.tipo_aplicacion_id),
            producto_id: producto ? Number(producto) : null,
            fecha_hora: fechaHora,
            cantidad: cantidad === "" ? null : Number(cantidad),
            unidad: values.unidad.trim() || null,
            aireacion_activa: values.aireacion_activa,
            observaciones: values.observaciones.trim() || null,
          });
        })}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Fecha y hora de aplicación">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Aireación">
            <label className="flex items-center gap-2 rounded-lg border border-[var(--bf-border)] px-3 py-2">
              <input type="checkbox" {...form.register("aireacion_activa")} />
              <span>Aireación activa durante la preparación</span>
            </label>
          </Field>
          <Field label="Tipo de aplicación">
            <select className="bf-input" {...form.register("tipo_aplicacion_id", { valueAsNumber: true, onChange: () => form.setValue("producto_id", "") })}>
              {(tiposQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.nombre}</option>)}
            </select>
          </Field>
          <Field label="Insumo">
            <select className="bf-input" disabled={!productosFiltrados.length} {...form.register("producto_id")}>
              <option value="">{productosFiltrados.length ? "Seleccione un insumo" : "Sin producto requerido"}</option>
              {productosFiltrados.map((row) => <option key={row.id} value={row.id}>{etiquetaProducto(row.nombre, row.codigo)}</option>)}
            </select>
          </Field>
          <Field label="Cantidad">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("cantidad")} />
          </Field>
          <Field label="Unidad">
            <input className="bf-input" {...form.register("unidad")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            Si la cantidad es mayor que 0, el sistema descuenta automáticamente el insumo del inventario y deja trazabilidad asociada al lote.
          </p>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || !puedeCrear}>
            {mutation.isPending ? "Guardando…" : "Registrar acondicionamiento"}
          </button>
        </form>
      </Modal>
    </div>
  );
}
