import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import {
  createEventoEnergia,
  listEquipos,
  listEventosEnergia,
  updateEventoEnergia,
} from "../../api/equipment";
import { apiErrorMessage } from "../../utils/apiError";
import { datetimeLocalToIso, formatDateTime, formatNumber, toDatetimeLocalValue } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { EventoEnergia, EventoEnergiaCreate } from "../../types/equipment";

export function EnergiaPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [closing, setClosing] = useState<EventoEnergia | null>(null);
  const [fin, setFin] = useState(toDatetimeLocalValue());
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarEventoEnergia");
  const puedeActualizar = can(user?.rol, "actualizarEventoEnergia");

  const query = useQuery({ queryKey: ["eventos-energia"], queryFn: () => listEventosEnergia() });
  const equiposQuery = useQuery({
    queryKey: ["equipos", { soloActivos: false }],
    queryFn: () => listEquipos({ soloActivos: false }),
  });
  const equipos = useMemo(
    () => new Map((equiposQuery.data ?? []).map((row) => [row.id, row])),
    [equiposQuery.data],
  );
  const form = useForm({
    defaultValues: {
      fecha_hora_inicio: toDatetimeLocalValue(),
      fecha_hora_fin: "",
      tipo: "CORTE",
      respaldo_activado: false,
      equipo_respaldo_id: "",
      observaciones: "",
    },
  });
  const respaldo = form.watch("respaldo_activado");

  const createMut = useMutation({
    mutationFn: (data: EventoEnergiaCreate) => createEventoEnergia(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["eventos-energia"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, fecha_hora_fin }: { id: number; fecha_hora_fin: string }) =>
      updateEventoEnergia(id, { fecha_hora_fin }),
    onSuccess: async () => {
      setClosing(null);
      await queryClient.invalidateQueries({ queryKey: ["eventos-energia"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <PageHeader
        title="Energía"
        description="Eventos de energía. La duración en minutos la calcula el backend al registrar el fin. tipo es texto del API (default CORTE); no hay catálogo."
        actions={
          puedeRegistrar ? (
            <button
              type="button"
              className="bf-btn-primary"
              onClick={() => {
                setFormError(null);
                form.reset({
                  fecha_hora_inicio: toDatetimeLocalValue(),
                  fecha_hora_fin: "",
                  tipo: "CORTE",
                  respaldo_activado: false,
                  equipo_respaldo_id: "",
                  observaciones: "",
                });
                setOpen(true);
              }}
            >
              Registrar evento
            </button>
          ) : null
        }
      />

      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: EventoEnergia) => row.id}
          empty="No hay eventos de energía."
          columns={[
            { key: "inicio", header: "Inicio", render: (row) => formatDateTime(row.fecha_hora_inicio) },
            {
              key: "fin",
              header: "Fin",
              render: (row) => (row.fecha_hora_fin ? formatDateTime(row.fecha_hora_fin) : "Abierto"),
            },
            {
              key: "dur",
              header: "Duración (min)",
              render: (row) => (row.duracion_minutos == null ? "—" : formatNumber(row.duracion_minutos)),
            },
            { key: "tipo", header: "Tipo", render: (row) => row.tipo },
            {
              key: "respaldo",
              header: "Respaldo",
              render: (row) => (
                <StatusBadge label={row.respaldo_activado ? "Activado" : "No"} tone={row.respaldo_activado ? "warn" : "neutral"} />
              ),
            },
            {
              key: "eq",
              header: "Equipo respaldo",
              render: (row) =>
                row.equipo_respaldo_id == null
                  ? "—"
                  : (equipos.get(row.equipo_respaldo_id)?.codigo ?? `#${row.equipo_respaldo_id}`),
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
            {
              key: "acc",
              header: "",
              render: (row) =>
                puedeActualizar && !row.fecha_hora_fin ? (
                  <button
                    type="button"
                    className="bf-btn-secondary !py-1 text-xs"
                    onClick={() => {
                      setFormError(null);
                      setFin(toDatetimeLocalValue());
                      setClosing(row);
                    }}
                  >
                    Cerrar evento
                  </button>
                ) : null,
            },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar evento de energía" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const finValue = values.fecha_hora_fin.trim();
            const equipo = values.equipo_respaldo_id.trim();
            createMut.mutate({
              fecha_hora_inicio: datetimeLocalToIso(values.fecha_hora_inicio),
              fecha_hora_fin: finValue ? datetimeLocalToIso(finValue) : null,
              tipo: values.tipo.trim() || "CORTE",
              respaldo_activado: values.respaldo_activado,
              equipo_respaldo_id: equipo === "" ? null : Number(equipo),
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Inicio">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora_inicio", { required: true })} />
          </Field>
          <Field label="Fin (opcional; si se omite el evento queda abierto)">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora_fin")} />
          </Field>
          <Field label="Tipo (texto del API)">
            <input className="bf-input" {...form.register("tipo")} />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...form.register("respaldo_activado")} />
            Respaldo activado
          </label>
          {respaldo ? (
            <Field label="Equipo de respaldo (obligatorio si hay respaldo)">
              <select className="bf-input" {...form.register("equipo_respaldo_id")}>
                <option value="">Seleccione</option>
                {(equiposQuery.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo} · {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            No se envía duracion_minutos: el servidor la calcula cuando hay fecha de fin.
          </p>
          <button type="submit" className="bf-btn-primary" disabled={createMut.isPending}>
            {createMut.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>

      <Modal open={Boolean(closing)} title="Cerrar evento" onClose={() => setClosing(null)}>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!closing) return;
            updateMut.mutate({ id: closing.id, fecha_hora_fin: datetimeLocalToIso(fin) });
          }}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <p className="text-sm text-[var(--bf-muted)]">
            Inicio: {closing ? formatDateTime(closing.fecha_hora_inicio) : "—"}
          </p>
          <Field label="Fecha y hora de fin">
            <input type="datetime-local" className="bf-input" required value={fin} onChange={(e) => setFin(e.target.value)} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">PUT con fecha_hora_fin. El backend asigna duracion_minutos.</p>
          <button type="submit" className="bf-btn-primary" disabled={updateMut.isPending}>
            {updateMut.isPending ? "Guardando…" : "Cerrar"}
          </button>
        </form>
      </Modal>
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
