import { useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
import { createEstanque, listEstanques, listLotes, updateEstanque } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDate, formatNumber, uniqueById } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Estanque, EstanqueCreate, EstanqueUpdate, Lote } from "../../types/production";

type EstanqueForm = {
  codigo: string;
  nombre: string;
  diametro: number;
  profundidad: number;
  estado_id: number;
  activo: boolean;
};

export function EstanquesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Estanque | null>(null);
  const [creating, setCreating] = useState(false);
  const [toToggle, setToToggle] = useState<Estanque | null>(null);
  const [historialDe, setHistorialDe] = useState<Estanque | null>(null);
  const verComparativo = searchParams.get("comparativo") === "1";

  const puedeCrear = can(user?.rol, "crearEstanque");
  const puedeEditar = can(user?.rol, "editarEstanque");

  const query = useQuery({
    queryKey: ["estanques", incluirInactivos],
    queryFn: () => listEstanques(!incluirInactivos),
  });

  // Una sola consulta de lotes para toda la tabla: identifica el lote activo de
  // cada estanque y alimenta el historial.
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });

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

  const estados = useMemo(
    () => uniqueById((query.data ?? []).map((row) => row.estado)),
    [query.data],
  );

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
      diametro: 0,
      profundidad: 0,
      estado_id: estados[0]?.id ?? 0,
      activo: true,
    });
    setCreating(true);
  }

  function openEdit(row: Estanque) {
    setFormError(null);
    form.reset({
      codigo: row.codigo,
      nombre: row.nombre,
      diametro: row.diametro,
      profundidad: row.profundidad,
      estado_id: row.estado_id,
      activo: row.activo,
    });
    setEditing(row);
  }

  function onCreate(values: EstanqueForm) {
    if (!values.estado_id) {
      setFormError("El formulario de alta requiere un catálogo que la API no expone.");
      return;
    }
    createMut.mutate({
      codigo: values.codigo.trim(),
      nombre: values.nombre.trim(),
      diametro: Number(values.diametro),
      profundidad: Number(values.profundidad),
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

  const catalogoEstadosDisponible = estados.length > 0;
  const estadosEdicion = editing ? uniqueById([...estados, editing.estado]) : estados;

  return (
    <div>
      <PageHeader
        title="Estanques"
        description="Unidades de producción. No hay borrado físico: se desactivan con PUT activo=false."
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
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                if (verComparativo) next.delete("comparativo");
                else next.set("comparativo", "1");
                setSearchParams(next);
              }}
            >
              {verComparativo ? "Ocultar comparativo" : "Comparativo analítico"}
            </button>
            {puedeCrear ? (
              <button type="button" className="bf-btn-primary" onClick={openCreate}>
                Nuevo estanque
              </button>
            ) : null}
          </div>
        }
      />

      {verComparativo ? <ComparativoEstanquesPanel soloActivos={!incluirInactivos} /> : null}

      {query.isLoading ? <LoadingState label="Cargando estanques…" /> : null}
      {query.isError ? (
        <div className="space-y-3">
          <ErrorAlert message={apiErrorMessage(query.error)} />
          <button type="button" className="bf-btn-primary" onClick={() => void query.refetch()}>
            Reintentar
          </button>
        </div>
      ) : null}

      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay estanques para mostrar."
          columns={[
            { key: "codigo", header: "Código" },
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
                    to={`/produccion/lotes/${activo.id}?tab=analisis`}
                    className="font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    {activo.codigo} · Análisis
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
          <ErrorAlert message="El formulario de alta requiere un catálogo que la API no expone. No hay GET de estados_estanque; solo se pueden reutilizar estados ya devueltos en estanques existentes." />
        ) : (
          <form className="space-y-3" onSubmit={form.handleSubmit(onCreate)}>
            {formError ? <ErrorAlert message={formError} /> : null}
            <Field label="Código">
              <input className="bf-input" {...form.register("codigo", { required: true })} />
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
                {...form.register("diametro", { required: true, valueAsNumber: true })}
              />
            </Field>
            <Field label="Profundidad">
              <input
                type="number"
                step="any"
                min="0"
                className="bf-input"
                {...form.register("profundidad", { required: true, valueAsNumber: true })}
              />
            </Field>
            <Field label="Estado">
              <select className="bf-input" {...form.register("estado_id", { valueAsNumber: true, required: true })}>
                {estados.map((estado) => (
                  <option key={estado.id} value={estado.id}>
                    {estado.nombre}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-[var(--bf-muted)]">
                Opciones tomadas de estanques ya listados. La API no expone el catálogo completo.
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
              {...form.register("diametro", { required: true, valueAsNumber: true })}
            />
          </Field>
          <Field label="Profundidad">
            <input
              type="number"
              step="any"
              min="0"
              className="bf-input"
              {...form.register("profundidad", { required: true, valueAsNumber: true })}
            />
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...form.register("estado_id", { valueAsNumber: true, required: true })}>
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
                    to={`/produccion/lotes/${row.id}?tab=historial`}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Historial
                  </Link>
                  <Link
                    to={`/produccion/lotes/${row.id}?tab=analisis`}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Análisis
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
