import { useMemo, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { getAlarma, listEstadosAlarma, updateAlarma } from "../../api/alarms";
import { listEquipos, listEventosEnergia } from "../../api/equipment";
import { listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDateTime } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { AlarmaUpdate, EstadoAlarma } from "../../types/alarms";

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

function estadoIdByNombre(estados: EstadoAlarma[] | undefined, nombre: string): number | undefined {
  return estados?.find((row) => row.nombre === nombre)?.id;
}

export function AlarmaDetallePage() {
  const { id } = useParams();
  const alarmaId = Number(id);
  const invalid = !Number.isInteger(alarmaId) || alarmaId <= 0;
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [transition, setTransition] = useState<"ATENDIDA" | "CERRADA" | null>(null);
  const [observaciones, setObservaciones] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const puedeActualizar = can(user?.rol, "actualizarAlarma");

  const query = useQuery({
    queryKey: ["alarma", alarmaId],
    queryFn: () => getAlarma(alarmaId),
    enabled: !invalid,
  });
  const estadosQuery = useQuery({ queryKey: ["estados-alarma"], queryFn: listEstadosAlarma });
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const equiposQuery = useQuery({
    queryKey: ["equipos", { soloActivos: false }],
    queryFn: () => listEquipos({ soloActivos: false }),
  });
  const eventosQuery = useQuery({ queryKey: ["eventos-energia"], queryFn: () => listEventosEnergia() });

  const lotes = useMemo(() => new Map((lotesQuery.data ?? []).map((row) => [row.id, row])), [lotesQuery.data]);
  const equipos = useMemo(
    () => new Map((equiposQuery.data ?? []).map((row) => [row.id, row])),
    [equiposQuery.data],
  );
  const eventos = useMemo(
    () => new Map((eventosQuery.data ?? []).map((row) => [row.id, row])),
    [eventosQuery.data],
  );

  const updateMut = useMutation({
    mutationFn: (data: AlarmaUpdate) => updateAlarma(alarmaId, data),
    onSuccess: async () => {
      setTransition(null);
      setObservaciones("");
      await queryClient.invalidateQueries({ queryKey: ["alarma", alarmaId] });
      await queryClient.invalidateQueries({ queryKey: ["alarmas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  if (invalid) {
    return <ErrorAlert message="Identificador de alarma inválido." />;
  }
  if (query.isLoading) {
    return <LoadingState label="Cargando alarma…" />;
  }
  if (query.isError) {
    return (
      <div className="space-y-3">
        <ErrorAlert message={apiErrorMessage(query.error)} />
        <Link to="/alarmas" className="bf-btn-secondary inline-flex">
          Volver a alarmas
        </Link>
      </div>
    );
  }

  const alarma = query.data;
  if (!alarma) return null;

  const lote = alarma.lote_id ? lotes.get(alarma.lote_id) : undefined;
  const equipo = alarma.equipo_id ? equipos.get(alarma.equipo_id) : undefined;
  const evento = alarma.evento_energia_id ? eventos.get(alarma.evento_energia_id) : undefined;

  return (
    <div>
      <div className="mb-4">
        <Link to="/alarmas" className="text-sm text-[var(--bf-accent)]">
          ← Alarmas
        </Link>
      </div>
      <div className="rounded-2xl border border-[var(--bf-border)] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--bf-accent)]">Alarma</p>
            <h1 className="font-display text-2xl font-semibold text-[var(--bf-ink)]">{alarma.titulo}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={alarma.nivel.nombre} tone={toneNivel(alarma.nivel.nombre)} />
            <StatusBadge label={alarma.estado.nombre} tone={toneEstado(alarma.estado.nombre)} />
          </div>
        </div>
        <p className="mt-3 whitespace-pre-wrap text-sm text-[var(--bf-ink)]">{alarma.mensaje}</p>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Info label="Fecha" value={formatDateTime(alarma.fecha_hora)} />
          <Info label="Tipo" value={alarma.tipo.nombre} />
          <Info label="Nivel" value={alarma.nivel.nombre} />
          <Info label="Estado" value={alarma.estado.nombre} />
          <Info
            label="Lote"
            value={
              alarma.lote_id == null ? (
                "—"
              ) : (
                <Link to={`/produccion/lotes/${alarma.lote_id}`} className="text-[var(--bf-accent)]">
                  {lote?.codigo ?? `#${alarma.lote_id}`}
                </Link>
              )
            }
          />
          <Info
            label="Equipo"
            value={
              alarma.equipo_id == null ? "—" : (equipo ? `${equipo.codigo} · ${equipo.nombre}` : `#${alarma.equipo_id}`)
            }
          />
          <Info
            label="Evento de energía"
            value={
              alarma.evento_energia_id == null
                ? "—"
                : evento
                  ? `${evento.tipo} · ${formatDateTime(evento.fecha_hora_inicio)}`
                  : `#${alarma.evento_energia_id}`
            }
          />
          <Info label="Fecha atención" value={alarma.fecha_atencion ? formatDateTime(alarma.fecha_atencion) : "—"} />
          <Info label="Atendida por" value={alarma.atendida_por == null ? "—" : `#${alarma.atendida_por}`} />
          <Info label="Registrada" value={formatDateTime(alarma.created_at)} />
        </dl>
        <p className="mt-4 text-sm text-[var(--bf-muted)]">{alarma.observaciones || "Sin observaciones."}</p>
        {puedeActualizar ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {alarma.estado.nombre === "PENDIENTE" ? (
              <button
                type="button"
                className="bf-btn-primary"
                onClick={() => {
                  setFormError(null);
                  setObservaciones("");
                  setTransition("ATENDIDA");
                }}
              >
                Atender
              </button>
            ) : null}
            {alarma.estado.nombre === "PENDIENTE" || alarma.estado.nombre === "ATENDIDA" ? (
              <button
                type="button"
                className="bf-btn-secondary"
                onClick={() => {
                  setFormError(null);
                  setObservaciones("");
                  setTransition("CERRADA");
                }}
              >
                Cerrar
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      <Modal open={Boolean(transition)} title={transition === "ATENDIDA" ? "Atender alarma" : "Cerrar alarma"} onClose={() => setTransition(null)}>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!transition) return;
            const estadoId = estadoIdByNombre(estadosQuery.data, transition);
            if (!estadoId) {
              setFormError("No se encontró el estado en el catálogo.");
              return;
            }
            const data: AlarmaUpdate = { estado_alarma_id: estadoId };
            if (observaciones.trim()) data.observaciones = observaciones.trim();
            updateMut.mutate(data);
          }}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <p className="text-sm text-[var(--bf-muted)]">PUT /alarmas/:id con estado_alarma_id. El backend asigna atendida_por y fecha_atencion.</p>
          <Field label="Observaciones (opcional)">
            <textarea
              className="bf-input min-h-20"
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
            />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={updateMut.isPending}>
            {updateMut.isPending ? "Guardando…" : "Confirmar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">{label}</dt>
      <dd className="mt-1 text-sm text-[var(--bf-ink)]">{value}</dd>
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
