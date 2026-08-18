import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { createAlarma, listAlarmas, listEstadosAlarma, listNivelesAlarma, listTiposAlarma, updateAlarma } from "../../api/alarms";
import { listEquipos, listEventosEnergia } from "../../api/equipment";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { datetimeLocalToIso, formatDateTime } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Alarma, AlarmaCreate, AlarmaUpdate, EstadoAlarma } from "../../types/alarms";

const ESTADOS_TAB = ["PENDIENTE", "ATENDIDA", "CERRADA"] as const;
type EstadoTab = (typeof ESTADOS_TAB)[number];

type CreateForm = {
  tipo_alarma_id: number;
  nivel_alarma_id: number;
  lote_id: string;
  equipo_id: string;
  evento_energia_id: string;
  fecha_hora: string;
  titulo: string;
  mensaje: string;
  observaciones: string;
};

function toneEstado(nombre: string) {
  if (nombre === "PENDIENTE") return "warn" as const;
  if (nombre === "ATENDIDA") return "info" as const;
  if (nombre === "CERRADA") return "ok" as const;
  return "neutral" as const;
}

function toneNivel(nombre: string) {
  if (nombre === "CRITICA" || nombre === "ALTA") return "danger" as const;
  if (nombre === "MEDIA") return "warn" as const;
  return "neutral" as const;
}

function dateToIsoStart(value: string): string {
  return datetimeLocalToIso(`${value}T00:00:00`);
}

function dateToIsoEnd(value: string): string {
  return datetimeLocalToIso(`${value}T23:59:59`);
}

function estadoIdByNombre(estados: EstadoAlarma[] | undefined, nombre: string): number | undefined {
  return estados?.find((row) => row.nombre === nombre)?.id;
}

export function AlarmasPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const estadoNombre = ESTADOS_TAB.includes(params.get("estado") as EstadoTab)
    ? (params.get("estado") as EstadoTab)
    : undefined;
  const tipoId = Number(params.get("tipo_id") ?? "") || undefined;
  const nivelId = Number(params.get("nivel_id") ?? "") || undefined;
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const equipoId = Number(params.get("equipo_id") ?? "") || undefined;
  const fechaDesde = params.get("fecha_desde") ?? "";
  const fechaHasta = params.get("fecha_hasta") ?? "";
  const [creating, setCreating] = useState(false);
  const [transition, setTransition] = useState<{ alarma: Alarma; estadoNombre: "ATENDIDA" | "CERRADA" } | null>(
    null,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarAlarma");
  const puedeActualizar = can(user?.rol, "actualizarAlarma");
  const form = useForm<CreateForm>();

  const tiposQuery = useQuery({ queryKey: ["tipos-alarma"], queryFn: () => listTiposAlarma(false) });
  const nivelesQuery = useQuery({ queryKey: ["niveles-alarma"], queryFn: listNivelesAlarma });
  const estadosQuery = useQuery({ queryKey: ["estados-alarma"], queryFn: listEstadosAlarma });
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const equiposQuery = useQuery({
    queryKey: ["equipos", { soloActivos: false }],
    queryFn: () => listEquipos({ soloActivos: false }),
  });
  const eventosQuery = useQuery({ queryKey: ["eventos-energia"], queryFn: () => listEventosEnergia() });

  const pendienteId = estadoIdByNombre(estadosQuery.data, "PENDIENTE");
  const estadoFiltroId = estadoNombre ? estadoIdByNombre(estadosQuery.data, estadoNombre) : undefined;

  const pendientesQuery = useQuery({
    queryKey: ["alarmas", { estadoAlarmaId: pendienteId }],
    queryFn: () => listAlarmas({ estadoAlarmaId: pendienteId }),
    enabled: Boolean(pendienteId),
  });

  const listQuery = useQuery({
    queryKey: [
      "alarmas",
      {
        estadoAlarmaId: estadoFiltroId,
        tipoAlarmaId: tipoId,
        nivelAlarmaId: nivelId,
        loteId,
        equipoId,
        fechaDesde,
        fechaHasta,
      },
    ],
    queryFn: () =>
      listAlarmas({
        estadoAlarmaId: estadoFiltroId,
        tipoAlarmaId: tipoId,
        nivelAlarmaId: nivelId,
        loteId,
        equipoId,
        fechaDesde: fechaDesde ? dateToIsoStart(fechaDesde) : undefined,
        fechaHasta: fechaHasta ? dateToIsoEnd(fechaHasta) : undefined,
      }),
    enabled: !estadoNombre || Boolean(estadoFiltroId),
  });

  const lotes = useMemo(() => new Map((lotesQuery.data ?? []).map((row) => [row.id, row])), [lotesQuery.data]);
  const equipos = useMemo(
    () => new Map((equiposQuery.data ?? []).map((row) => [row.id, row])),
    [equiposQuery.data],
  );

  const createMut = useMutation({
    mutationFn: (data: AlarmaCreate) => createAlarma(data),
    onSuccess: async () => {
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["alarmas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlarmaUpdate }) => updateAlarma(id, data),
    onSuccess: async () => {
      setTransition(null);
      await queryClient.invalidateQueries({ queryKey: ["alarmas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function setEstadoTab(nombre?: EstadoTab) {
    const next = new URLSearchParams(params);
    if (nombre) next.set("estado", nombre);
    else next.delete("estado");
    setParams(next);
  }

  function openCreate() {
    setFormError(null);
    form.reset({
      tipo_alarma_id: tiposQuery.data?.find((row) => row.activo)?.id ?? tiposQuery.data?.[0]?.id ?? 0,
      nivel_alarma_id: nivelesQuery.data?.[0]?.id ?? 0,
      lote_id: loteId ? String(loteId) : "",
      equipo_id: equipoId ? String(equipoId) : "",
      evento_energia_id: "",
      fecha_hora: "",
      titulo: "",
      mensaje: "",
      observaciones: "",
    });
    setCreating(true);
  }

  const pendientes = pendientesQuery.data?.length ?? 0;

  return (
    <div>
      <PageHeader
        title="Alarmas"
        description="Sistema general de alarmas. El stock bajo de productos está en Inventario; no se mezcla aquí."
        actions={
          puedeRegistrar ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Nueva alarma
            </button>
          ) : null
        }
      />

      <div className="mb-4 max-w-xs">
        <KpiCard
          label="Alarmas pendientes"
          value={pendientesQuery.isLoading ? "…" : pendientes}
          to="/alarmas?estado=PENDIENTE"
          emphasize={pendientes > 0}
        />
      </div>

      <div className="mb-4 flex gap-1 border-b border-[var(--bf-border)]">
        <TabButton active={!estadoNombre} onClick={() => setEstadoTab()}>
          Todas
        </TabButton>
        {ESTADOS_TAB.map((nombre) => (
          <TabButton key={nombre} active={estadoNombre === nombre} onClick={() => setEstadoTab(nombre)}>
            {nombre}
          </TabButton>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Tipo</span>
          <select className="bf-input" value={tipoId ?? ""} onChange={(e) => setParam("tipo_id", e.target.value)}>
            <option value="">Todos</option>
            {(tiposQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Nivel</span>
          <select className="bf-input" value={nivelId ?? ""} onChange={(e) => setParam("nivel_id", e.target.value)}>
            <option value="">Todos</option>
            {(nivelesQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Lote</span>
          <select className="bf-input" value={loteId ?? ""} onChange={(e) => setParam("lote_id", e.target.value)}>
            <option value="">Todos</option>
            {(lotesQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.codigo}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Equipo</span>
          <select className="bf-input" value={equipoId ?? ""} onChange={(e) => setParam("equipo_id", e.target.value)}>
            <option value="">Todos</option>
            {(equiposQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.codigo}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Desde</span>
          <input
            type="date"
            className="bf-input"
            value={fechaDesde}
            onChange={(e) => setParam("fecha_desde", e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Hasta</span>
          <input
            type="date"
            className="bf-input"
            value={fechaHasta}
            onChange={(e) => setParam("fecha_hasta", e.target.value)}
          />
        </label>
      </div>

      {listQuery.isLoading ? <LoadingState /> : null}
      {listQuery.isError ? <ErrorAlert message={apiErrorMessage(listQuery.error)} /> : null}
      {listQuery.data ? (
        <DataTable
          rows={listQuery.data}
          rowKey={(row) => row.id}
          empty="No hay alarmas."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            { key: "tipo", header: "Tipo", render: (row) => row.tipo.nombre },
            {
              key: "nivel",
              header: "Nivel",
              render: (row) => <StatusBadge label={row.nivel.nombre} tone={toneNivel(row.nivel.nombre)} />,
            },
            { key: "titulo", header: "Título", render: (row) => row.titulo },
            {
              key: "estado",
              header: "Estado",
              render: (row) => <StatusBadge label={row.estado.nombre} tone={toneEstado(row.estado.nombre)} />,
            },
            {
              key: "rel",
              header: "Relación",
              render: (row) =>
                row.lote_id
                  ? `Lote ${lotes.get(row.lote_id)?.codigo ?? `#${row.lote_id}`}`
                  : row.equipo_id
                    ? `Equipo ${equipos.get(row.equipo_id)?.codigo ?? `#${row.equipo_id}`}`
                    : row.evento_energia_id
                      ? `Energía #${row.evento_energia_id}`
                      : "—",
            },
            {
              key: "ops",
              header: "",
              render: (row) => (
                <div className="flex flex-wrap justify-end gap-2">
                  <Link to={`/alarmas/${row.id}`} className="text-xs text-[var(--bf-accent)]">
                    Ver
                  </Link>
                  {puedeActualizar && row.estado.nombre === "PENDIENTE" ? (
                    <button
                      type="button"
                      className="bf-btn-secondary !py-1 text-xs"
                      onClick={() => {
                        setFormError(null);
                        setTransition({ alarma: row, estadoNombre: "ATENDIDA" });
                      }}
                    >
                      Atender
                    </button>
                  ) : null}
                  {puedeActualizar && (row.estado.nombre === "PENDIENTE" || row.estado.nombre === "ATENDIDA") ? (
                    <button
                      type="button"
                      className="bf-btn-secondary !py-1 text-xs"
                      onClick={() => {
                        setFormError(null);
                        setTransition({ alarma: row, estadoNombre: "CERRADA" });
                      }}
                    >
                      Cerrar
                    </button>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      ) : null}

      <Modal open={creating} title="Nueva alarma" size="lg" onClose={() => setCreating(false)}>
        <form
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={form.handleSubmit((values) => {
            const payload: AlarmaCreate = {
              tipo_alarma_id: Number(values.tipo_alarma_id),
              nivel_alarma_id: Number(values.nivel_alarma_id),
              titulo: values.titulo.trim(),
              mensaje: values.mensaje.trim(),
              observaciones: values.observaciones.trim() || null,
            };
            if (values.lote_id) payload.lote_id = Number(values.lote_id);
            if (values.equipo_id) payload.equipo_id = Number(values.equipo_id);
            if (values.evento_energia_id) payload.evento_energia_id = Number(values.evento_energia_id);
            if (values.fecha_hora) payload.fecha_hora = datetimeLocalToIso(values.fecha_hora);
            createMut.mutate(payload);
          })}
        >
          {formError ? (
            <div className="sm:col-span-2">
              <ErrorAlert message={formError} />
            </div>
          ) : null}
          <Field label="Tipo">
            <select className="bf-input" {...form.register("tipo_alarma_id", { valueAsNumber: true })}>
              {(tiposQuery.data ?? [])
                .filter((row) => row.activo)
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Nivel">
            <select className="bf-input" {...form.register("nivel_alarma_id", { valueAsNumber: true })}>
              {(nivelesQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Título">
            <input className="bf-input" {...form.register("titulo", { required: true })} />
          </Field>
          <Field label="Fecha y hora (opcional; si se omite el API usa ahora)">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora")} />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Mensaje">
              <textarea className="bf-input min-h-20" {...form.register("mensaje", { required: true })} />
            </Field>
          </div>
          <Field label="Lote (opcional)">
            <select className="bf-input" {...form.register("lote_id")}>
              <option value="">Ninguno</option>
              {(lotesQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.codigo}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Equipo (opcional)">
            <select className="bf-input" {...form.register("equipo_id")}>
              <option value="">Ninguno</option>
              {(equiposQuery.data ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.codigo} · {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <div className="sm:col-span-2">
            <Field label="Evento de energía (opcional)">
              <select className="bf-input" {...form.register("evento_energia_id")}>
                <option value="">Ninguno</option>
                {(eventosQuery.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    #{row.id} · {row.tipo} · {formatDateTime(row.fecha_hora_inicio)}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="sm:col-span-2">
            <Field label="Observaciones">
              <textarea className="bf-input min-h-16" {...form.register("observaciones")} />
            </Field>
          </div>
          <p className="sm:col-span-2 text-xs text-[var(--bf-muted)]">
            El estado inicial lo asigna el API (PENDIENTE). No se envía estado_alarma_id.
          </p>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="bf-btn-primary"
              disabled={createMut.isPending || (tiposQuery.data ?? []).length === 0}
            >
              {createMut.isPending ? "Guardando…" : "Registrar"}
            </button>
          </div>
        </form>
      </Modal>

      <TransitionModal
        key={transition ? `${transition.alarma.id}-${transition.estadoNombre}` : "closed"}
        open={Boolean(transition)}
        title={transition?.estadoNombre === "ATENDIDA" ? "Atender alarma" : "Cerrar alarma"}
        formError={formError}
        pending={updateMut.isPending}
        onClose={() => setTransition(null)}
        onSubmit={(observaciones) => {
          if (!transition) return;
          const estadoId = estadoIdByNombre(estadosQuery.data, transition.estadoNombre);
          if (!estadoId) {
            setFormError("No se encontró el estado en el catálogo.");
            return;
          }
          const data: AlarmaUpdate = { estado_alarma_id: estadoId };
          if (observaciones) data.observaciones = observaciones;
          updateMut.mutate({ id: transition.alarma.id, data });
        }}
      />
    </div>
  );
}

function TransitionModal({
  open,
  title,
  formError,
  pending,
  onClose,
  onSubmit,
}: {
  open: boolean;
  title: string;
  formError: string | null;
  pending: boolean;
  onClose: () => void;
  onSubmit: (observaciones: string) => void;
}) {
  const [observaciones, setObservaciones] = useState("");
  return (
    <Modal
      open={open}
      title={title}
      onClose={() => {
        setObservaciones("");
        onClose();
      }}
    >
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(observaciones.trim());
        }}
      >
        {formError ? <ErrorAlert message={formError} /> : null}
        <p className="text-sm text-[var(--bf-muted)]">PUT envía estado_alarma_id del catálogo. Observaciones es opcional.</p>
        <Field label="Observaciones (opcional)">
          <textarea
            className="bf-input min-h-20"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
        </Field>
        <button type="submit" className="bf-btn-primary" disabled={pending}>
          {pending ? "Guardando…" : "Confirmar"}
        </button>
      </form>
    </Modal>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      className={`px-3 py-2 text-sm ${
        active ? "border-b-2 border-[var(--bf-accent)] font-medium text-[var(--bf-ink)]" : "text-[var(--bf-muted)]"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
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
