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
  listMedicionesBiofloc,
  listProductosActivos,
  listReferenciasBiofloc,
  listTiposAplicacionBiofloc,
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
        description="Mediciones de volumen sedimentable y aplicaciones. No se genera movimiento de inventario."
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
              render: (row) =>
                row.cantidad == null
                  ? "—"
                  : `${formatNumber(row.cantidad, { maximumFractionDigits: 4 })}${row.unidad ? ` ${row.unidad}` : ""}`,
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
            mutation.mutate({
              lote_id: Number(values.lote_id),
              tipo_aplicacion_id: Number(values.tipo_aplicacion_id),
              producto_id: producto === "" ? null : Number(producto),
              fecha_hora: fechaHora,
              cantidad: cantidad === "" ? null : Number(cantidad),
              unidad: values.unidad.trim() || null,
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
            <select className="bf-input" {...form.register("tipo_aplicacion_id", { valueAsNumber: true })}>
              {(tiposQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Producto (opcional)">
            <select className="bf-input" {...form.register("producto_id")}>
              <option value="">Ninguno</option>
              {(productosQuery.data ?? []).map((row) => (
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
            Esta aplicación no descuenta inventario. No se llama a movimientos.
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
