import { useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ComparativoEstanquesPanel } from "./ComparativoEstanquesPanel";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { createEstanque, listEstadosEstanque, listEstanques, listLotes, updateEstanque } from "../../api/production";
import { getComparativoEstanques } from "../../api/analisis";
import { pathFichaEstanque } from "./fichaPaths";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDate, formatNumber, uniqueById } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Estanque, EstanqueCreate, EstanqueUpdate, Lote } from "../../types/production";
import type { EstanqueComparativo } from "../../types/analisis";

type EstanqueForm = {
  codigo: string;
  nombre: string;
  diametro: string;
  profundidad: string;
  estado_id: string;
  activo: boolean;
};

export function EstanquesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Estanque | null>(null);
  const [creating, setCreating] = useState(false);
  const [toToggle, setToToggle] = useState<Estanque | null>(null);
  const [historialDe, setHistorialDe] = useState<Estanque | null>(null);
  const verComparativo = searchParams.get("comparativo") !== "0";

  const [vistaTabla, setVistaTabla] = useState(false);

  const puedeCrear = can(user?.rol, "crearEstanque");
  const puedeEditar = can(user?.rol, "editarEstanque");

  const query = useQuery({
    queryKey: ["estanques", incluirInactivos],
    queryFn: () => listEstanques(!incluirInactivos),
  });

  const comparativoQuery = useQuery({
    queryKey: ["analisis-estanques", incluirInactivos],
    queryFn: () => getComparativoEstanques(!incluirInactivos),
  });

  const comparativoMap = useMemo(() => {
    const m = new Map<number, EstanqueComparativo>();
    for (const e of comparativoQuery.data?.estanques ?? []) m.set(e.estanque_id, e);
    return m;
  }, [comparativoQuery.data]);

  // Una sola consulta de lotes para toda la tabla: identifica el lote activo de
  // cada estanque y alimenta el historial.
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const estadosQuery = useQuery({
    queryKey: ["estados-estanque"],
    queryFn: () => listEstadosEstanque(false),
  });

  const lotesPorEstanque = useMemo(() => {
    const mapa = new Map<number, Lote[]>();
    for (const lote of lotesQuery.data ?? []) {
      const lista = mapa.get(lote.estanque_id) ?? [];
      lista.push(lote);
      mapa.set(lote.estanque_id, lista);
    }
    for (const lista of mapa.values()) {
      lista.sort((a, b) => b.fecha_siembra.localeCompare(a.fecha_siembra));
    }
    return mapa;
  }, [lotesQuery.data]);

  function loteActivoDe(estanqueId: number): Lote | undefined {
    return lotesPorEstanque.get(estanqueId)?.find((lote) => lote.estado.nombre === "ACTIVO");
  }

  const estados = useMemo(() => {
    const catalogo = estadosQuery.data ?? [];
    if (catalogo.length > 0) return catalogo;
    return uniqueById((query.data ?? []).map((row) => row.estado));
  }, [estadosQuery.data, query.data]);

  const form = useForm<EstanqueForm>();

  const createMut = useMutation({
    mutationFn: (data: EstanqueCreate) => createEstanque(data),
    onSuccess: async () => {
      setCreating(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["estanques"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: EstanqueUpdate }) => updateEstanque(id, data),
    onSuccess: async () => {
      setEditing(null);
      setToToggle(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["estanques"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      codigo: "",
      nombre: "",
      diametro: "",
      profundidad: "",
      estado_id: "",
      activo: true,
    });
    setCreating(true);
  }

  function openEdit(row: Estanque) {
    setFormError(null);
    form.reset({
      codigo: row.codigo,
      nombre: row.nombre,
      diametro: String(row.diametro),
      profundidad: String(row.profundidad),
      estado_id: String(row.estado_id),
      activo: row.activo,
    });
    setEditing(row);
  }

  function onCreate(values: EstanqueForm) {
    if (!values.estado_id) {
      setFormError("Seleccione un estado de estanque.");
      return;
    }
    const diametro = Number(values.diametro);
    const profundidad = Number(values.profundidad);
    if (!Number.isFinite(diametro) || diametro <= 0 || !Number.isFinite(profundidad) || profundidad <= 0) {
      setFormError("Diámetro y profundidad deben ser mayores que 0.");
      return;
    }
    createMut.mutate({
      codigo: values.codigo.trim(),
      nombre: values.nombre.trim(),
      diametro,
      profundidad,
      estado_id: Number(values.estado_id),
      activo: values.activo,
    });
  }

  function onEdit(values: EstanqueForm) {
    if (!editing) return;
    updateMut.mutate({
      id: editing.id,
      data: {
        nombre: values.nombre.trim(),
        diametro: Number(values.diametro),
        profundidad: Number(values.profundidad),
        estado_id: Number(values.estado_id),
        activo: values.activo,
      },
    });
  }

  const catalogoEstadosDisponible = estados.filter((estado) => estado.activo).length > 0;
  const estadosAlta = estados.filter((estado) => estado.activo);
  const estadosEdicion = editing ? uniqueById([...estados, editing.estado]) : estados;

  return (
    <div>
      <PageHeader
        title="Estanques"
        description="Centro de la granja. Resumen, comparación y ficha de cada estanque."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-[var(--bf-muted)]">
              <input
                type="checkbox"
                checked={incluirInactivos}
                onChange={(event) => setIncluirInactivos(event.target.checked)}
              />
              Incluir inactivos
            </label>
            <button
              type="button"
              className="bf-btn-secondary"
              onClick={() => setVistaTabla(!vistaTabla)}
            >
              {vistaTabla ? "Vista tarjetas" : "Vista tabla"}
            </button>
            <button
              type="button"
              className="bf-btn-secondary"
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                if (verComparativo) next.set("comparativo", "0");
                else next.delete("comparativo");
                setSearchParams(next);
              }}
            >
              {verComparativo ? "Ocultar comparación" : "Mostrar comparación"}
            </button>
            {puedeCrear ? (
              <button type="button" className="bf-btn-primary" onClick={openCreate}>
                Nuevo estanque
              </button>
            ) : null}
          </div>
        }
      />

      {query.data && query.data.length > 0 ? (
        <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-xl border border-[var(--bf-border)] bg-white px-4 py-3 bf-enter">
            <p className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">Total</p>
            <p className="mt-1 font-display text-2xl font-semibold">{formatNumber(query.data.length)}</p>
          </article>
          <article className="rounded-xl border border-[var(--bf-border)] bg-white px-4 py-3 bf-enter">
            <p className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">Activos</p>
            <p className="mt-1 font-display text-2xl font-semibold">{formatNumber(query.data.filter((row) => row.activo).length)}</p>
          </article>
          <article className="rounded-xl border border-[var(--bf-border)] bg-white px-4 py-3 bf-enter">
            <p className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">Ocupados</p>
            <p className="mt-1 font-display text-2xl font-semibold">
              {formatNumber(query.data.filter((row) => Boolean(loteActivoDe(row.id))).length)}
            </p>
          </article>
          <article className="rounded-xl border border-[var(--bf-border)] bg-white px-4 py-3 bf-enter">
            <p className="text-xs uppercase tracking-wide text-[var(--bf-muted)]">Disponibles</p>
            <p className="mt-1 font-display text-2xl font-semibold">
              {formatNumber(query.data.filter((row) => row.activo && !loteActivoDe(row.id)).length)}
            </p>
          </article>
        </div>
      ) : null}

      {verComparativo ? <ComparativoEstanquesPanel soloActivos={!incluirInactivos} mostrarResumen={false} /> : null}

      {query.isLoading ? <LoadingState label="Cargando estanques…" /> : null}
      {query.isError ? (
        <div className="space-y-3">
          <ErrorAlert message={apiErrorMessage(query.error)} />
          <button type="button" className="bf-btn-primary" onClick={() => void query.refetch()}>
            Reintentar
          </button>
        </div>
      ) : null}

      {query.data && !vistaTabla ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {query.data.map((row) => {
            const comp = comparativoMap.get(row.id);
            const loteActivo = loteActivoDe(row.id);
            const ocupado = Boolean(loteActivo || comp?.lote_id);
            return (
              <article
                key={row.id}
                className="group relative cursor-pointer rounded-xl border border-[var(--bf-border)] bg-white p-4 transition hover:shadow-md hover:border-[var(--bf-accent)]/40 bf-enter"
                onClick={() => navigate(pathFichaEstanque(row.id))}
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div>
                    <p className="font-display text-base font-semibold text-[var(--bf-ink)]">{row.codigo}</p>
                    <p className="text-xs text-[var(--bf-muted)]">{row.nombre}</p>
                  </div>
                  <StatusBadge
                    label={ocupado ? "Ocupado" : "Disponible"}
                    tone={ocupado ? "ok" : "neutral"}
                  />
                </div>

                {comp?.lote_id ? (
                  <div className="mt-3 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Especie</span>
                      <span className="font-medium">{comp.especie ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Lote</span>
                      <span className="font-medium text-[var(--bf-accent)]">{comp.lote_codigo}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Siembra</span>
                      <span>{comp.fecha_siembra ? formatDate(comp.fecha_siembra) : "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Peso prom.</span>
                      <span>{comp.peso_promedio_g != null ? `${formatNumber(comp.peso_promedio_g, { maximumFractionDigits: 1 })} g` : "N/D"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Biomasa</span>
                      <span>{comp.biomasa_actual_kg != null ? `${formatNumber(comp.biomasa_actual_kg, { maximumFractionDigits: 1 })} kg` : "N/D"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--bf-muted)]">Población</span>
                      <span>{comp.poblacion_estimada != null ? formatNumber(comp.poblacion_estimada) : "N/D"}</span>
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 text-center text-xs text-[var(--bf-muted)]">Sin siembra activa</p>
                )}

                <div className="mt-3 flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {puedeEditar ? (
                    <button
                      type="button"
                      className="bf-btn-secondary !py-0.5 !px-2 text-[10px]"
                      onClick={(e) => { e.stopPropagation(); openEdit(row); }}
                    >
                      Editar
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {query.data && vistaTabla ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="Sin estanques registrados"
          onRowClick={(row) => navigate(pathFichaEstanque(row.id))}
          columns={[
            {
              key: "codigo",
              header: "Código",
              render: (row) => (
                <Link
                  to={pathFichaEstanque(row.id)}
                  className="font-medium text-[var(--bf-accent)] hover:underline"
                  onClick={(event) => event.stopPropagation()}
                >
                  {row.codigo}
                </Link>
              ),
            },
            { key: "nombre", header: "Nombre" },
            {
              key: "diametro",
              header: "Diámetro",
              render: (row) => formatNumber(row.diametro, { maximumFractionDigits: 2 }),
            },
            {
              key: "profundidad",
              header: "Profundidad",
              render: (row) => formatNumber(row.profundidad, { maximumFractionDigits: 2 }),
            },
            {
              key: "estado",
              header: "Estado",
              render: (row) => <StatusBadge label={row.estado.nombre} tone="info" />,
            },
            {
              key: "activo",
              header: "Activo",
              render: (row) => (
                <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "danger"} />
              ),
            },
            {
              key: "lote_activo",
              header: "Lote activo",
              render: (row) => {
                const activo = loteActivoDe(row.id);
                if (lotesQuery.isLoading) return "…";
                if (!activo) return <span className="text-[var(--bf-muted)]">Sin lote activo</span>;
                return (
                  <Link
                    to={pathFichaEstanque(row.id, { loteId: activo.id })}
                    className="font-medium text-[var(--bf-accent)] hover:underline"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {activo.codigo}
                  </Link>
                );
              },
            },
            {
              key: "acciones",
              header: "",
              render: (row) => (
                <div className="flex flex-wrap gap-2" onClick={(event) => event.stopPropagation()}>
                  <button
                    type="button"
                    className="bf-btn-primary !py-1 text-xs"
                    onClick={() => navigate(pathFichaEstanque(row.id))}
                  >
                    Ver estanque
                  </button>
                  <button
                    type="button"
                    className="bf-btn-secondary !py-1 text-xs"
                    onClick={() => setHistorialDe(row)}
                  >
                    Historial
                  </button>
                  {puedeEditar ? (
                    <>
                      <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => openEdit(row)}>
                        Editar
                      </button>
                      <button
                        type="button"
                        className="bf-btn-secondary !py-1 text-xs"
                        onClick={() => setToToggle(row)}
                      >
                        {row.activo ? "Desactivar" : "Activar"}
                      </button>
                    </>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      ) : null}

      <Modal
        open={creating}
        title="Nuevo estanque"
        onClose={() => {
          setCreating(false);
          setFormError(null);
        }}
      >
        {!catalogoEstadosDisponible ? (
          <ErrorAlert message="No hay estados de estanque activos en el catálogo. No se puede crear el estanque." />
        ) : (
          <form className="space-y-3" onSubmit={form.handleSubmit(onCreate)}>
            {formError ? <ErrorAlert message={formError} /> : null}
            <Field label="Código">
              <input className="bf-input" {...form.register("codigo", { required: true })} />
            </Field>
            <Field label="Nombre">
              <input className="bf-input" {...form.register("nombre", { required: true })} />
            </Field>
            <Field label="Diámetro (m)">
              <input
                type="number"
                step="any"
                min="0"
                className="bf-input"
                placeholder="Ingrese el diámetro"
                {...form.register("diametro", { required: true })}
              />
            </Field>
            <Field label="Profundidad (m)">
              <input
                type="number"
                step="any"
                min="0"
                className="bf-input"
                placeholder="Ingrese la profundidad"
                {...form.register("profundidad", { required: true })}
              />
            </Field>
            <Field label="Estado">
              <select className="bf-input" {...form.register("estado_id", { required: true })}>
                <option value="">Seleccione un estado</option>
                {estadosAlta.map((estado) => (
                  <option key={estado.id} value={estado.id}>
                    {estado.nombre}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-[var(--bf-muted)]">
                Catálogo GET /estados-estanque. Solo se listan estados existentes; no se inventan.
              </p>
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...form.register("activo")} />
              Activo
            </label>
            <button type="submit" className="bf-btn-primary" disabled={createMut.isPending}>
              {createMut.isPending ? "Guardando…" : "Crear"}
            </button>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(editing)}
        title={`Editar ${editing?.codigo ?? ""}`}
        onClose={() => {
          setEditing(null);
          setFormError(null);
        }}
      >
        <form className="space-y-3" onSubmit={form.handleSubmit(onEdit)}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Código">
            <input className="bf-input" disabled {...form.register("codigo")} />
          </Field>
          <Field label="Nombre">
            <input className="bf-input" {...form.register("nombre", { required: true })} />
          </Field>
          <Field label="Diámetro">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              {...form.register("diametro", { required: true })}
            />
          </Field>
          <Field label="Profundidad">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              {...form.register("profundidad", { required: true })}
            />
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...form.register("estado_id", { required: true })}>
              {estadosEdicion.map((estado) => (
                <option key={estado.id} value={estado.id}>
                  {estado.nombre}
                </option>
              ))}
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...form.register("activo")} />
            Activo
          </label>
          <button type="submit" className="bf-btn-primary" disabled={updateMut.isPending}>
            {updateMut.isPending ? "Guardando…" : "Guardar"}
          </button>
        </form>
      </Modal>

      <Modal
        open={Boolean(historialDe)}
        title={`Historial de ${historialDe?.codigo ?? ""}`}
        onClose={() => setHistorialDe(null)}
      >
        <p className="mb-3 text-xs text-[var(--bf-muted)]">
          Lotes del estanque, del más reciente al más antiguo. Cada lote mantiene su propio análisis: no se mezclan
          datos entre lotes.
        </p>
        <DataTable
          rows={historialDe ? (lotesPorEstanque.get(historialDe.id) ?? []) : []}
          rowKey={(row) => row.id}
          empty="Este estanque todavía no tiene lotes."
          columns={[
            { key: "codigo", header: "Código" },
            { key: "especie", header: "Especie", render: (row) => row.especie.nombre_comun },
            { key: "siembra", header: "Siembra", render: (row) => formatDate(row.fecha_siembra) },
            {
              key: "cierre",
              header: "Cierre",
              render: (row) => (row.fecha_cierre ? formatDate(row.fecha_cierre) : "—"),
            },
            {
              key: "estado",
              header: "Estado",
              render: (row) => (
                <StatusBadge label={row.estado.nombre} tone={row.estado.nombre === "ACTIVO" ? "ok" : "neutral"} />
              ),
            },
            {
              key: "ficha",
              header: "",
              render: (row) => (
                <span className="flex flex-wrap gap-2">
                  <Link
                    to={pathFichaEstanque(historialDe?.id ?? 0, { loteId: row.id, tab: "historial" })}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Historial
                  </Link>
                  <Link
                    to={pathFichaEstanque(historialDe?.id ?? 0, { loteId: row.id })}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Entrar
                  </Link>
                </span>
              ),
            },
          ]}
        />
      </Modal>

      <ConfirmDialog
        open={Boolean(toToggle)}
        title={toToggle?.activo ? "Desactivar estanque" : "Activar estanque"}
        description="No hay DELETE. El cambio se envía con PUT activo."
        confirmLabel={toToggle?.activo ? "Desactivar" : "Activar"}
        onCancel={() => setToToggle(null)}
        onConfirm={() => {
          if (!toToggle) return;
          updateMut.mutate({ id: toToggle.id, data: { activo: !toToggle.activo } });
        }}
      />
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
