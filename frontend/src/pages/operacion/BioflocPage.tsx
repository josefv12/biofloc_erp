import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import { StatusBadge } from "../../components/StatusBadge";
import {
  createAplicacionBiofloc,
  createMedicionBiofloc,
  listAplicacionesBiofloc,
  listMedicionesAgua,
  listMedicionesBiofloc,
  listParametrosAgua,
  listProductosActivos,
  listReferenciasBiofloc,
  listTiposAplicacionBiofloc,
  listUnidades,
} from "../../api/operations";
import { getLote, listLotes } from "../../api/production";
import { listUsuarios } from "../../api/users";
import { apiErrorMessage } from "../../utils/apiError";
import {
  etiquetaProducto,
  formatDateTime,
  formatNumber,
  toDatetimeLocalValue,
  withFechaHoraIso,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import { esLoteActivo, lotesActivos } from "../../utils/loteEstado";
import { cumplimientoPorRango, etiquetaCumplimiento, toneCumplimiento } from "../../utils/analisisStatus";
import { toNumber } from "../../utils/series";
import type {
  AplicacionBiofloc,
  AplicacionBioflocCreate,
  MedicionBiofloc,
  MedicionBioflocCreate,
  Producto,
  TipoAplicacionBiofloc,
} from "../../types/operations";
import type { Lote } from "../../types/production";

type BioTab = "mediciones" | "aplicaciones";

export function BioflocPage() {
  const [params, setParams] = useSearchParams();
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const tab: BioTab = params.get("tab") === "aplicaciones" ? "aplicaciones" : "mediciones";
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });

  function setTab(siguiente: BioTab) {
    const next = new URLSearchParams(params);
    if (siguiente === "aplicaciones") next.set("tab", "aplicaciones");
    else next.delete("tab");
    setParams(next);
  }

  return (
    <div>
      <PageHeader
        title="Biofloc"
        description="Mediciones de volumen sedimentable y aplicaciones de insumos Biofloc. Las aplicaciones con cantidad descuentan inventario."
      />
      <label className="mb-4 block max-w-xs text-sm">
        <span className="mb-1 block text-[var(--bf-muted)]">Lote</span>
        <select
          className="bf-input"
          value={loteId ?? ""}
          onChange={(event) => {
            const next = new URLSearchParams(params);
            if (event.target.value) next.set("lote_id", event.target.value);
            else next.delete("lote_id");
            setParams(next);
          }}
        >
          <option value="">Todos</option>
          {(lotesQuery.data ?? []).map((lote) => (
            <option key={lote.id} value={lote.id}>
              {lote.codigo}
            </option>
          ))}
        </select>
      </label>
      {loteId ? <ContextoOperativoBiofloc loteId={loteId} /> : null}
      <div className="mb-4 flex gap-1 border-b border-[var(--bf-border)]">
        <TabButton active={tab === "mediciones"} onClick={() => setTab("mediciones")}>
          Mediciones
        </TabButton>
        <TabButton active={tab === "aplicaciones"} onClick={() => setTab("aplicaciones")}>
          Aplicaciones
        </TabButton>
      </div>
      {tab === "mediciones" ? (
        <MedicionesBioflocPanel loteId={loteId} lotes={lotesQuery.data ?? []} compact={false} />
      ) : (
        <AplicacionesBioflocPanel loteId={loteId} lotes={lotesQuery.data ?? []} compact={false} />
      )}
    </div>
  );
}


function ContextoOperativoBiofloc({ loteId }: { loteId: number }) {
  const loteQuery = useQuery({
    queryKey: ["lote", loteId],
    queryFn: () => getLote(loteId),
  });
  const aguaQuery = useQuery({
    queryKey: ["mediciones-agua", loteId],
    queryFn: () => listMedicionesAgua({ lote_id: loteId }),
  });
  const parametrosQuery = useQuery({
    queryKey: ["parametros-agua"],
    queryFn: () => listParametrosAgua(true),
  });
  const bioflocQuery = useQuery({
    queryKey: ["mediciones-biofloc", loteId],
    queryFn: () => listMedicionesBiofloc(loteId),
  });

  const lote = loteQuery.data;
  const dias = useMemo(() => {
    if (!lote?.fecha_siembra) return null;
    const [year, month, day] = lote.fecha_siembra.slice(0, 10).split("-").map(Number);
    const siembra = Date.UTC(year, month - 1, day);
    const hoy = new Date();
    const hoyUtc = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
    return Math.max(0, Math.floor((hoyUtc - siembra) / 86400000));
  }, [lote?.fecha_siembra]);
  const semana = dias == null ? null : Math.floor(dias / 7) + 1;
  const parametros = useMemo(
    () => new Map((parametrosQuery.data ?? []).map((item) => [item.id, item])),
    [parametrosQuery.data],
  );
  const ultimasAgua = useMemo(() => {
    const ordenadas = [...(aguaQuery.data ?? [])].sort((a, b) =>
      b.fecha_hora.localeCompare(a.fecha_hora),
    );
    const vistos = new Set<number>();
    return ordenadas.filter((item) => {
      if (vistos.has(item.parametro_id)) return false;
      vistos.add(item.parametro_id);
      return true;
    });
  }, [aguaQuery.data]);
  const ultimaBiofloc = [...(bioflocQuery.data ?? [])].sort((a, b) =>
    b.fecha_hora.localeCompare(a.fecha_hora),
  )[0];

  if (loteQuery.isLoading) return <div className="mb-4"><LoadingState /></div>;
  if (loteQuery.isError || !lote) {
    return <div className="mb-4"><ErrorAlert message={apiErrorMessage(loteQuery.error)} /></div>;
  }

  return (
    <section className="mb-5 rounded-xl border border-[var(--bf-border)] bg-[var(--bf-surface)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-display text-base font-semibold text-[var(--bf-ink)]">
            Contexto del lote · {lote.codigo}
          </h2>
          <p className="text-xs text-[var(--bf-muted)]">
            {lote.especie.nombre_comun} · {lote.etapa_productiva.nombre} · {lote.estado.nombre}
          </p>
        </div>
        <span className="rounded-full border border-[var(--bf-border)] px-3 py-1 text-xs text-[var(--bf-muted)]">
          {dias == null ? "Siembra N/D" : `Día ${dias} · Semana ${semana}`}
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <p className="text-xs text-[var(--bf-muted)]">Fecha de siembra</p>
          <p className="font-medium text-[var(--bf-ink)]">{lote.fecha_siembra.slice(0, 10)}</p>
        </div>
        <div>
          <p className="text-xs text-[var(--bf-muted)]">Peces sembrados</p>
          <p className="font-medium text-[var(--bf-ink)]">{formatNumber(lote.cantidad_sembrada)}</p>
        </div>
        <div>
          <p className="text-xs text-[var(--bf-muted)]">Peso inicial promedio</p>
          <p className="font-medium text-[var(--bf-ink)]">
            {lote.peso_inicial_promedio_g == null ? "N/D" : `${formatNumber(lote.peso_inicial_promedio_g, { maximumFractionDigits: 2 })} g`}
          </p>
        </div>
        <div>
          <p className="text-xs text-[var(--bf-muted)]">Ciclo estimado</p>
          <p className="font-medium text-[var(--bf-ink)]">{lote.meses_ciclo_estimado} meses</p>
        </div>
        <div>
          <p className="text-xs text-[var(--bf-muted)]">Cosecha estimada</p>
          <p className="font-medium text-[var(--bf-ink)]">{lote.fecha_estimada_cosecha.slice(0, 10)}</p>
        </div>
      </div>
      {dias != null ? (
        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-[var(--bf-muted)]">Avance calendario del ciclo</span>
            <span className="font-medium text-[var(--bf-ink)]">{Math.min(100, Math.round((dias / Math.max(1, Math.ceil((new Date(lote.fecha_estimada_cosecha).getTime() - new Date(lote.fecha_siembra).getTime()) / 86400000))) * 100))}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[var(--bf-bg)]">
            <div
              className="h-full rounded-full bg-[var(--bf-accent)]"
              style={{ width: `${Math.min(100, Math.max(0, Math.round((dias / Math.max(1, Math.ceil((new Date(lote.fecha_estimada_cosecha).getTime() - new Date(lote.fecha_siembra).getTime()) / 86400000))) * 100))}%` }}
            />
          </div>
        </div>
      ) : null}
      <div className="mt-4 border-t border-[var(--bf-border)] pt-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
          Últimas mediciones de calidad de agua
        </p>
        {aguaQuery.isLoading ? <p className="text-sm text-[var(--bf-muted)]">Cargando mediciones…</p> : null}
        {aguaQuery.isError ? <ErrorAlert message={apiErrorMessage(aguaQuery.error)} /> : null}
        {!aguaQuery.isLoading && !aguaQuery.isError && ultimasAgua.length === 0 ? (
          <p className="text-sm text-[var(--bf-muted)]">No hay mediciones de agua registradas para este lote.</p>
        ) : null}
        {ultimasAgua.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {ultimasAgua.map((item) => (
              <div key={item.parametro_id} className="rounded-lg bg-[var(--bf-bg)] p-2">
                <p className="text-xs text-[var(--bf-muted)]">
                  {parametros.get(item.parametro_id)?.nombre ?? `Parámetro #${item.parametro_id}`}
                </p>
                <p className="font-medium text-[var(--bf-ink)]">
                  {formatNumber(item.valor, { maximumFractionDigits: 3 })} {parametros.get(item.parametro_id)?.unidad ?? ""}
                </p>
                <p className="text-[11px] text-[var(--bf-muted)]">{formatDateTime(item.fecha_hora)}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
      <div className="mt-3 rounded-lg border border-[var(--bf-border)] p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--bf-muted)]">
          Verificación previa a aplicaciones
        </p>
        <p className="text-xs text-[var(--bf-muted)]">
          Las mediciones siguientes son registros históricos, no necesariamente condiciones actuales del estanque.
          Confirme fecha y vigencia antes de decidir cualquier aplicación.
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--bf-ink)]">
          <li>Volumen sedimentable: {ultimaBiofloc ? `última lectura ${formatDateTime(ultimaBiofloc.fecha_hora)}` : "sin registro para este lote"}.</li>
          <li>Calidad del agua: {ultimasAgua.length ? `${ultimasAgua.length} parámetros con historial; revisar fechas individuales` : "sin registros para este lote"}.</li>
          <li>Biomasa y población actualizadas: no verificadas en este panel.</li>
          <li>Salinidad/cloruros y fichas técnicas de insumos: no verificados en este panel.</li>
        </ul>
        <p className="mt-2 text-xs font-medium text-[var(--bf-ink)]">
          Estado: información insuficiente para calcular o validar dosis automáticamente.
        </p>
      </div>
      <div className="mt-3 text-xs text-[var(--bf-muted)]">
        Último volumen sedimentable: {ultimaBiofloc
          ? `${formatNumber(ultimaBiofloc.volumen_sedimentable, { maximumFractionDigits: 2 })} ${ultimaBiofloc.unidad} · ${formatDateTime(ultimaBiofloc.fecha_hora)}`
          : "Sin registro"}.
      </div>
      <p className="mt-3 rounded-lg border border-amber-300/50 bg-amber-50/50 px-3 py-2 text-xs text-amber-900">
        El número de semana es un cálculo calendario desde la siembra. No constituye una dosis recomendada.
        Las cantidades presupuestales de insumos deben contrastarse con mediciones actuales, biomasa y fichas técnicas antes de aplicar.
      </p>
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`px-3 py-2 text-sm ${
        active
          ? "border-b-2 border-[var(--bf-accent)] font-medium text-[var(--bf-ink)]"
          : "text-[var(--bf-muted)]"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function MedicionesBioflocPanel({
  loteId,
  lotes,
  compact,
}: {
  loteId?: number;
  lotes: Lote[];
  compact: boolean;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["mediciones-biofloc", loteId],
    queryFn: () => listMedicionesBiofloc(loteId),
  });
  const loteQuery = useQuery({
    queryKey: ["lote", loteId],
    queryFn: () => getLote(loteId!),
    enabled: Boolean(loteId),
  });
  const refsQuery = useQuery({
    queryKey: ["referencias-biofloc", loteQuery.data?.especie_id, loteQuery.data?.etapa_productiva_id],
    queryFn: () =>
      listReferenciasBiofloc({
        especie_id: loteQuery.data!.especie_id,
        etapa_productiva_id: loteQuery.data!.etapa_productiva_id,
        indicador: "VOLUMEN_SEDIMENTABLE",
        solo_activos: true,
      }),
    enabled: Boolean(loteQuery.data),
  });
  const refVolumen = refsQuery.data?.[0];
  const form = useForm({
    defaultValues: {
      lote_id: loteId ?? 0,
      fecha_hora: toDatetimeLocalValue(),
      volumen_sedimentable: "",
      unidad: "",
      relacion_cn: "",
      observaciones: "",
    },
  });
  const mutation = useMutation({
    mutationFn: (data: MedicionBioflocCreate) => createMedicionBiofloc(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["mediciones-biofloc"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-estanques"] });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });
  const lotesMap = useMemo(() => new Map(lotes.map((row) => [row.id, row])), [lotes]);
  const enProduccion = lotesActivos(lotes);
  const loteContexto = loteId ? lotes.find((row) => row.id === loteId) : undefined;
  const puedeRegistrarLote = !loteId || esLoteActivo(loteContexto);
  const usuariosQuery = useQuery({ queryKey: ["usuarios"], queryFn: () => listUsuarios(false) });
  const usuarios = useMemo(
    () => new Map((usuariosQuery.data ?? []).map((row) => [row.id, row.nombre])),
    [usuariosQuery.data],
  );
  const rows = compact ? (query.data ?? []).slice(0, 5) : (query.data ?? []);
  const unidadCatalogo = query.data?.[0]?.unidad ?? "";

  return (
    <div>
      <PanelToolbar
        compact={compact}
        loteId={loteId}
        allHref={`/operacion/biofloc?lote_id=${loteId ?? ""}`}
        onCreate={
          can(user?.rol, "registrarBiofloc") && puedeRegistrarLote
            ? () => {
                setFormError(null);
                form.reset({
                  lote_id: loteId ?? enProduccion[0]?.id ?? 0,
                  fecha_hora: toDatetimeLocalValue(),
                  volumen_sedimentable: "",
                  unidad: unidadCatalogo,
                  relacion_cn: "",
                  observaciones: "",
                });
                setOpen(true);
              }
            : undefined
        }
        createLabel="Registrar medición"
        hint={compact ? "Últimas mediciones Biofloc" : "Historial de mediciones"}
      />
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={rows}
          rowKey={(row: MedicionBiofloc) => row.id}
          empty="No hay mediciones Biofloc."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            ...(!loteId
              ? [
                  {
                    key: "lote",
                    header: "Lote",
                    render: (row: MedicionBiofloc) => lotesMap.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
                  },
                ]
              : []),
            {
              key: "vol",
              header: "Volumen sedimentable",
              render: (row) =>
                `${formatNumber(row.volumen_sedimentable, { maximumFractionDigits: 2 })} ${row.unidad}`,
            },
            {
              key: "cn",
              header: "Relación C/N",
              render: (row) =>
                row.relacion_cn == null ? "—" : formatNumber(row.relacion_cn, { maximumFractionDigits: 3 }),
            },
            {
              key: "estado",
              header: "Estado",
              render: (row) => {
                if (!loteId) return "Seleccione un lote";
                const estado = cumplimientoPorRango(
                  toNumber(row.volumen_sedimentable),
                  refVolumen ? toNumber(refVolumen.valor_minimo) : null,
                  refVolumen ? toNumber(refVolumen.valor_maximo) : null,
                );
                if (estado === "NO_EVALUABLE") {
                  return <StatusBadge label="N/D — Sin referencia configurada" tone="neutral" />;
                }
                return <StatusBadge label={etiquetaCumplimiento(estado)} tone={toneCumplimiento(estado)} />;
              },
            },
            {
              key: "usuario",
              header: "Usuario",
              render: (row: MedicionBiofloc) => usuarios.get(row.registrado_por) ?? `#${row.registrado_por}`,
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar medición Biofloc" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            const cn = values.relacion_cn.trim();
            mutation.mutate({
              lote_id: Number(values.lote_id),
              fecha_hora: fechaHora,
              volumen_sedimentable: Number(values.volumen_sedimentable),
              unidad: values.unidad.trim() || "mL/L",
              relacion_cn: cn === "" ? null : Number(cn),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {loteId ? (
            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { valueAsNumber: true })}>
                {enProduccion.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Volumen sedimentable">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              {...form.register("volumen_sedimentable", { valueAsNumber: true })}
            />
          </Field>
          <Field label="Unidad">
            <input className="bf-input" {...form.register("unidad")} />
            <p className="mt-1 text-xs text-[var(--bf-muted)]">
              Use la unidad del catálogo o de la última medición. No se asume mL/L si el registro usa otra.
            </p>
          </Field>
          <Field label="Relación C/N (opcional)">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("relacion_cn")} />
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

export function AplicacionesBioflocPanel({
  loteId,
  lotes,
  compact,
}: {
  loteId?: number;
  lotes: Lote[];
  compact: boolean;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [stockMsg, setStockMsg] = useState<string | null>(null);
  const tiposQuery = useQuery({
    queryKey: ["tipos-aplicacion-biofloc"],
    queryFn: () => listTiposAplicacionBiofloc(true),
  });
  const productosQuery = useQuery({ queryKey: ["productos-activos"], queryFn: listProductosActivos });
  const unidadesQuery = useQuery({ queryKey: ["unidades"], queryFn: listUnidades });
  const query = useQuery({
    queryKey: ["aplicaciones-biofloc", loteId],
    queryFn: () => listAplicacionesBiofloc(loteId),
  });
  const tipos = useMemo(
    () => new Map((tiposQuery.data ?? []).map((row: TipoAplicacionBiofloc) => [row.id, row])),
    [tiposQuery.data],
  );
  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((row: Producto) => [row.id, row])),
    [productosQuery.data],
  );
  const lotesMap = useMemo(() => new Map(lotes.map((row) => [row.id, row])), [lotes]);
  const enProduccion = lotesActivos(lotes);
  const loteContexto = loteId ? lotes.find((row) => row.id === loteId) : undefined;
  const puedeRegistrarLote = !loteId || esLoteActivo(loteContexto);
  const form = useForm({
    defaultValues: {
      lote_id: loteId ?? 0,
      tipo_aplicacion_id: 0,
      producto_id: "",
      fecha_hora: toDatetimeLocalValue(),
      cantidad: "",
      unidad: "",
      observaciones: "",
    },
  });

  const tipoAplicacionId = form.watch("tipo_aplicacion_id");
  const productoIdSeleccionado = form.watch("producto_id");
  const tipoAplicacion = tipos.get(Number(tipoAplicacionId));
  const productoSeleccionado = productos.get(Number(productoIdSeleccionado));
  const unidades = useMemo(
    () => new Map((unidadesQuery.data ?? []).map((row) => [row.id, row])),
    [unidadesQuery.data],
  );
  const unidadInventario = productoSeleccionado
    ? unidades.get(productoSeleccionado.unidad_id)?.simbolo ?? ""
    : "";
  const productosBiofloc = useMemo(() => {
    const tipo = (tipoAplicacion?.nombre ?? "").toUpperCase();
    let patrones: RegExp[] = [];
    if (tipo.includes("PROBIOTICO")) patrones = [/probi[oó]tico/i];
    else if (tipo.includes("FUENTE_CARBONO")) patrones = [/melaza/i];
    else if (tipo.includes("CORRECTIVO")) patrones = [/sal\s*marina/i, /bicarbonato/i];
    return (productosQuery.data ?? []).filter((row: Producto) =>
      patrones.some((patron) => patron.test(row.nombre) || patron.test(row.codigo)),
    );
  }, [productosQuery.data, tipoAplicacion?.nombre]);
  const mutation = useMutation({
    mutationFn: (data: AplicacionBioflocCreate) => createAplicacionBiofloc(data),
    onSuccess: async (resp) => {
      setOpen(false);
      if (resp.stock_restante != null) {
        setStockMsg(`Inventario actualizado: ${resp.stock_restante.toFixed(2)} disponibles`);
        setTimeout(() => setStockMsg(null), 6000);
      }
      await queryClient.invalidateQueries({ queryKey: ["aplicaciones-biofloc"] });
      await queryClient.invalidateQueries({ queryKey: ["stock"] });
    },
    onError: (err) => setFormError(apiErrorMessage(err)),
  });
  const rows = compact ? (query.data ?? []).slice(0, 5) : (query.data ?? []);

  return (
    <div>
      {stockMsg ? (
        <div className="mb-3 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {stockMsg}
        </div>
      ) : null}
      <PanelToolbar
        compact={compact}
        loteId={loteId}
        allHref={`/operacion/biofloc?lote_id=${loteId ?? ""}&tab=aplicaciones`}
        onCreate={
          can(user?.rol, "registrarBiofloc") && puedeRegistrarLote
            ? () => {
                setFormError(null);
                form.reset({
                  lote_id: loteId ?? enProduccion[0]?.id ?? 0,
                  tipo_aplicacion_id: tiposQuery.data?.[0]?.id ?? 0,
                  producto_id: "",
                  fecha_hora: toDatetimeLocalValue(),
                  cantidad: "",
                  unidad: "",
                  observaciones: "",
                });
                setOpen(true);
              }
            : undefined
        }
        createLabel="Registrar aplicación"
        hint={compact ? "Últimas aplicaciones Biofloc" : "Historial de aplicaciones"}
      />
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={rows}
          rowKey={(row: AplicacionBiofloc) => row.id}
          empty="No hay aplicaciones Biofloc."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            ...(!loteId
              ? [
                  {
                    key: "lote",
                    header: "Lote",
                    render: (row: AplicacionBiofloc) => lotesMap.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
                  },
                ]
              : []),
            {
              key: "tipo",
              header: "Tipo",
              render: (row) => tipos.get(row.tipo_aplicacion_id)?.nombre ?? `#${row.tipo_aplicacion_id}`,
            },
            {
              key: "producto",
              header: "Producto",
              render: (row) =>
                row.producto_id == null
                  ? "—"
                  : (productos.get(row.producto_id)?.codigo ?? `#${row.producto_id}`),
            },
            {
              key: "cant",
              header: "Cantidad",
              render: (row) => {
                if (row.cantidad == null) return "—";
                // Algunas aplicaciones históricas guardaron cantidad sin unidad.
                // Mostrar la unidad base del producto evita dejar ambiguo el dato.
                const unidad = row.unidad || (row.producto_id != null
                  ? unidades.get(productos.get(row.producto_id)?.unidad_id ?? -1)?.simbolo
                  : undefined);
                return `${formatNumber(row.cantidad, { maximumFractionDigits: 4 })}${unidad ? ` ${unidad}` : ""}`;
              },
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar aplicación Biofloc" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const fechaHora = withFechaHoraIso(values.fecha_hora, setFormError);
            if (!fechaHora) return;
            const producto = values.producto_id.trim();
            const cantidad = values.cantidad.trim();
            if (cantidad !== "" && Number(cantidad) > 0 && producto === "") {
              setFormError("Seleccione un insumo Biofloc cuando registre una cantidad mayor que 0.");
              return;
            }
            mutation.mutate({
              lote_id: Number(values.lote_id),
              tipo_aplicacion_id: Number(values.tipo_aplicacion_id),
              producto_id: producto === "" ? null : Number(producto),
              fecha_hora: fechaHora,
              cantidad: cantidad === "" ? null : Number(cantidad),
              // Las salidas de inventario usan la unidad interna del producto.
              unidad: unidadInventario || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {loteId ? (
            <input type="hidden" {...form.register("lote_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { valueAsNumber: true })}>
                {enProduccion.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Tipo de aplicación">
            <select
              className="bf-input"
              {...form.register("tipo_aplicacion_id", {
                valueAsNumber: true,
                onChange: () => form.setValue("producto_id", ""),
              })}
            >
              {(tiposQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Producto">
            <select
              className="bf-input"
              disabled={productosBiofloc.length === 0}
              {...form.register("producto_id")}
            >
              <option value="">
                {productosBiofloc.length ? "Seleccione un insumo" : "No requiere producto"}
              </option>
              {productosBiofloc.map((row) => (
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
            <p className="mt-1 text-xs text-[var(--bf-muted)]">
              Si registra una cantidad mayor que 0, debe seleccionar un insumo.
            </p>
          </Field>
          <Field label="Unidad de inventario">
            <input className="bf-input" value={unidadInventario} readOnly placeholder="Seleccione primero un producto" />
            <p className="mt-1 text-xs text-[var(--bf-muted)]">
              Registre la cantidad en esta unidad. Es la unidad base usada por el inventario y el costeo; no escriba gramos si aquí aparece kg.
            </p>
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            Los consumos con cantidad mayor que 0 generan automáticamente una salida de inventario y afectan el costo de producción.
          </p>
          <button
            type="submit"
            className="bf-btn-primary"
            disabled={mutation.isPending || (tiposQuery.data ?? []).length === 0}
          >
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function PanelToolbar({
  compact,
  loteId,
  allHref,
  onCreate,
  createLabel,
  hint,
}: {
  compact: boolean;
  loteId?: number;
  allHref: string;
  onCreate?: () => void;
  createLabel: string;
  hint: string;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <p className="text-sm text-[var(--bf-muted)]">{hint}</p>
      <div className="flex gap-2">
        {compact && loteId ? (
          <Link to={allHref} className="bf-btn-secondary">
            Ver todas
          </Link>
        ) : null}
        {onCreate ? (
          <button type="button" className="bf-btn-primary" onClick={onCreate}>
            {createLabel}
          </button>
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
