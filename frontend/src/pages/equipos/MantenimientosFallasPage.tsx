import { useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
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
  createFalla,
  createMantenimiento,
  listEquipos,
  listFallas,
  listMantenimientos,
  listTiposMantenimiento,
  updateFalla,
} from "../../api/equipment";
import { apiErrorMessage } from "../../utils/apiError";
import {
  datetimeLocalToIso,
  formatCop,
  formatDate,
  formatDateTime,
  toDatetimeLocalValue,
} from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Falla, FallaCreate, FallaUpdate, Mantenimiento, MantenimientoCreate } from "../../types/equipment";

type TabId = "mantenimientos" | "fallas";

function todayDateInput(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function MantenimientosFallasPage() {
  const [params, setParams] = useSearchParams();
  const tab: TabId = params.get("tab") === "fallas" ? "fallas" : "mantenimientos";
  const equipoId = Number(params.get("equipo_id") ?? "") || undefined;
  const equiposQuery = useQuery({
    queryKey: ["equipos", { soloActivos: false }],
    queryFn: () => listEquipos({ soloActivos: false }),
  });

  return (
    <div>
      <PageHeader
        title="Mantenimiento y fallas"
        description="Mantenimientos inmutables. Las fallas se pueden actualizar con PUT (solución, impacto, costo, descripción)."
      />
      <label className="mb-4 block max-w-xs text-sm">
        <span className="mb-1 block text-[var(--bf-muted)]">Equipo</span>
        <select
          className="bf-input"
          value={equipoId ?? ""}
          onChange={(event) => {
            const next = new URLSearchParams(params);
            if (event.target.value) next.set("equipo_id", event.target.value);
            else next.delete("equipo_id");
            setParams(next);
          }}
        >
          <option value="">Todos</option>
          {(equiposQuery.data ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.codigo} · {row.nombre}
            </option>
          ))}
        </select>
      </label>
      <div className="mb-4 flex gap-1 border-b border-[var(--bf-border)]">
        <TabButton
          active={tab === "mantenimientos"}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.delete("tab");
            setParams(next);
          }}
        >
          Mantenimientos
        </TabButton>
        <TabButton
          active={tab === "fallas"}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set("tab", "fallas");
            setParams(next);
          }}
        >
          Fallas
        </TabButton>
      </div>
      {tab === "mantenimientos" ? (
        <MantenimientosPanel equipoId={equipoId} equipos={equiposQuery.data ?? []} />
      ) : (
        <FallasPanel equipoId={equipoId} equipos={equiposQuery.data ?? []} />
      )}
    </div>
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

function MantenimientosPanel({
  equipoId,
  equipos,
}: {
  equipoId?: number;
  equipos: { id: number; codigo: string; nombre: string }[];
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarMantenimiento");
  const query = useQuery({
    queryKey: ["mantenimientos", equipoId],
    queryFn: () => listMantenimientos({ equipoId }),
  });
  const tiposQuery = useQuery({
    queryKey: ["tipos-mantenimiento"],
    queryFn: () => listTiposMantenimiento(false),
  });
  const equiposMap = useMemo(() => new Map(equipos.map((row) => [row.id, row])), [equipos]);
  const tipos = useMemo(() => new Map((tiposQuery.data ?? []).map((row) => [row.id, row])), [tiposQuery.data]);
  const form = useForm({
    defaultValues: {
      equipo_id: 0,
      tipo_mantenimiento_id: 0,
      fecha: todayDateInput(),
      descripcion: "",
      costo: "0",
      proveedor: "",
      observaciones: "",
    },
  });
  const mutation = useMutation({
    mutationFn: (data: MantenimientoCreate) => createMantenimiento(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["mantenimientos"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        {puedeRegistrar ? (
          <button
            type="button"
            className="bf-btn-primary"
            onClick={() => {
              setFormError(null);
              form.reset({
                equipo_id: equipoId ?? equipos[0]?.id ?? 0,
                tipo_mantenimiento_id: tiposQuery.data?.find((row) => row.activo)?.id ?? tiposQuery.data?.[0]?.id ?? 0,
                fecha: todayDateInput(),
                descripcion: "",
                costo: "0",
                proveedor: "",
                observaciones: "",
              });
              setOpen(true);
            }}
          >
            Registrar mantenimiento
          </button>
        ) : null}
      </div>
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: Mantenimiento) => row.id}
          empty="No hay mantenimientos."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDate(row.fecha) },
            {
              key: "equipo",
              header: "Equipo",
              render: (row) => equiposMap.get(row.equipo_id)?.codigo ?? `#${row.equipo_id}`,
            },
            {
              key: "tipo",
              header: "Tipo",
              render: (row) => tipos.get(row.tipo_mantenimiento_id)?.nombre ?? `#${row.tipo_mantenimiento_id}`,
            },
            { key: "desc", header: "Descripción", render: (row) => row.descripcion },
            { key: "costo", header: "Costo", render: (row) => formatCop(row.costo) },
            { key: "proveedor", header: "Proveedor", render: (row) => row.proveedor || "—" },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}
      <Modal open={open} title="Registrar mantenimiento" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            mutation.mutate({
              equipo_id: Number(values.equipo_id),
              tipo_mantenimiento_id: Number(values.tipo_mantenimiento_id),
              fecha: values.fecha,
              descripcion: values.descripcion.trim(),
              costo: values.costo.trim() === "" ? 0 : Number(values.costo),
              proveedor: values.proveedor.trim() || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {equipoId ? (
            <input type="hidden" {...form.register("equipo_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Equipo">
              <select className="bf-input" {...form.register("equipo_id", { valueAsNumber: true })}>
                {equipos.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo} · {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Tipo de mantenimiento">
            <select className="bf-input" {...form.register("tipo_mantenimiento_id", { valueAsNumber: true })}>
              {(tiposQuery.data ?? [])
                .filter((row) => row.activo)
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Fecha">
            <input type="date" className="bf-input" {...form.register("fecha", { required: true })} />
          </Field>
          <Field label="Descripción">
            <input className="bf-input" {...form.register("descripcion", { required: true })} />
          </Field>
          <Field label="Costo">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("costo")} />
          </Field>
          <Field label="Proveedor (opcional)">
            <input className="bf-input" {...form.register("proveedor")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={mutation.isPending || equipos.length === 0}>
            {mutation.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>
    </div>
  );
}

function FallasPanel({
  equipoId,
  equipos,
}: {
  equipoId?: number;
  equipos: { id: number; codigo: string; nombre: string }[];
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [solving, setSolving] = useState<Falla | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [solucion, setSolucion] = useState("");
  const puedeRegistrar = can(user?.rol, "registrarFalla");
  const puedeActualizar = can(user?.rol, "actualizarFalla");
  const query = useQuery({
    queryKey: ["fallas", equipoId],
    queryFn: () => listFallas({ equipoId }),
  });
  const equiposMap = useMemo(() => new Map(equipos.map((row) => [row.id, row])), [equipos]);
  const form = useForm({
    defaultValues: {
      equipo_id: 0,
      fecha_hora: toDatetimeLocalValue(),
      descripcion: "",
      impacto: "",
      solucion: "",
      costo: "0",
    },
  });
  const createMut = useMutation({
    mutationFn: (data: FallaCreate) => createFalla(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["fallas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: FallaUpdate }) => updateFalla(id, data),
    onSuccess: async () => {
      setSolving(null);
      setSolucion("");
      await queryClient.invalidateQueries({ queryKey: ["fallas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        {puedeRegistrar ? (
          <button
            type="button"
            className="bf-btn-primary"
            onClick={() => {
              setFormError(null);
              form.reset({
                equipo_id: equipoId ?? equipos[0]?.id ?? 0,
                fecha_hora: toDatetimeLocalValue(),
                descripcion: "",
                impacto: "",
                solucion: "",
                costo: "0",
              });
              setOpen(true);
            }}
          >
            Registrar falla
          </button>
        ) : null}
      </div>
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: Falla) => row.id}
          empty="No hay fallas."
          columns={[
            { key: "fecha", header: "Fecha/hora", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "equipo",
              header: "Equipo",
              render: (row) => equiposMap.get(row.equipo_id)?.codigo ?? `#${row.equipo_id}`,
            },
            { key: "desc", header: "Descripción", render: (row) => row.descripcion },
            { key: "impacto", header: "Impacto", render: (row) => row.impacto || "—" },
            {
              key: "solucion",
              header: "Solución",
              render: (row) =>
                row.solucion ? (
                  row.solucion
                ) : (
                  <StatusBadge label="Sin solución" tone="warn" />
                ),
            },
            { key: "costo", header: "Costo", render: (row) => formatCop(row.costo) },
            {
              key: "acc",
              header: "",
              render: (row) =>
                puedeActualizar && !row.solucion ? (
                  <button
                    type="button"
                    className="bf-btn-secondary !py-1 text-xs"
                    onClick={() => {
                      setFormError(null);
                      setSolucion("");
                      setSolving(row);
                    }}
                  >
                    Registrar solución
                  </button>
                ) : null,
            },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar falla" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            createMut.mutate({
              equipo_id: Number(values.equipo_id),
              fecha_hora: datetimeLocalToIso(values.fecha_hora),
              descripcion: values.descripcion.trim(),
              impacto: values.impacto.trim() || null,
              solucion: values.solucion.trim() || null,
              costo: values.costo.trim() === "" ? 0 : Number(values.costo),
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          {equipoId ? (
            <input type="hidden" {...form.register("equipo_id", { valueAsNumber: true })} />
          ) : (
            <Field label="Equipo">
              <select className="bf-input" {...form.register("equipo_id", { valueAsNumber: true })}>
                {equipos.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo} · {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Fecha y hora">
            <input type="datetime-local" className="bf-input" {...form.register("fecha_hora", { required: true })} />
          </Field>
          <Field label="Descripción">
            <input className="bf-input" {...form.register("descripcion", { required: true })} />
          </Field>
          <Field label="Impacto (opcional, texto del API)">
            <input className="bf-input" {...form.register("impacto")} />
          </Field>
          <Field label="Solución (opcional)">
            <textarea className="bf-input min-h-20" {...form.register("solucion")} />
          </Field>
          <Field label="Costo">
            <input type="number" step="any" min="0" className="bf-input" {...form.register("costo")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={createMut.isPending || equipos.length === 0}>
            {createMut.isPending ? "Guardando…" : "Registrar"}
          </button>
        </form>
      </Modal>

      <Modal open={Boolean(solving)} title="Registrar solución" onClose={() => setSolving(null)}>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!solving) return;
            updateMut.mutate({ id: solving.id, data: { solucion: solucion.trim() } });
          }}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <p className="text-sm text-[var(--bf-muted)]">{solving?.descripcion}</p>
          <Field label="Solución">
            <textarea className="bf-input min-h-24" required value={solucion} onChange={(e) => setSolucion(e.target.value)} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">PUT /fallas/:id con el campo solucion. No hay catálogo de estados.</p>
          <button type="submit" className="bf-btn-primary" disabled={updateMut.isPending || !solucion.trim()}>
            {updateMut.isPending ? "Guardando…" : "Guardar solución"}
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
