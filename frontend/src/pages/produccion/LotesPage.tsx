import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { createLote, listEstadosLote, listEstanques, listEspecies, listEtapasProductivas, listLotes, updateLote } from "../../api/production";
import { pathFichaEstanque } from "./fichaPaths";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDate, formatNumber } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Lote, LoteCreate, LoteUpdate } from "../../types/production";

type LoteCreateForm = {
  codigo: string;
  estanque_id: number;
  especie_id: number;
  etapa_productiva_id: number;
  estado_id: number;
  fecha_siembra: string;
  fecha_cierre: string;
  cantidad_sembrada: number | "";
  peso_inicial_promedio_g: string;
  observaciones: string;
};

type LoteEditForm = {
  etapa_productiva_id: number;
  estado_id: number;
  fecha_cierre: string;
  observaciones: string;
};

export function LotesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Lote | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const puedeCrear = can(user?.rol, "crearLote");
  const puedeEditar = can(user?.rol, "editarLote");

  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const estanquesQuery = useQuery({
    queryKey: ["estanques", true],
    queryFn: () => listEstanques(false),
  });
  const especiesQuery = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });
  const etapasQuery = useQuery({
    queryKey: ["etapas-productivas", "catalog"],
    queryFn: () => listEtapasProductivas(false),
  });
  const estadosQuery = useQuery({
    queryKey: ["estados-lote", "catalog"],
    queryFn: () => listEstadosLote(false),
  });

  const estanques = useMemo(() => {
    const map = new Map((estanquesQuery.data ?? []).map((row) => [row.id, row]));
    return map;
  }, [estanquesQuery.data]);

  const especies = (especiesQuery.data ?? []).filter((row) => row.activo);
  const etapasActivas = (etapasQuery.data ?? []).filter((row) => row.activo);
  const estadosActivos = (estadosQuery.data ?? []).filter((row) => row.activo);
  const etapas = etapasQuery.data ?? [];
  const estados = estadosQuery.data ?? [];

  const catalogoAltaOk =
    especies.length > 0 &&
    etapasActivas.length > 0 &&
    estadosActivos.length > 0 &&
    (estanquesQuery.data?.length ?? 0) > 0;

  const createForm = useForm<LoteCreateForm>();
  const editForm = useForm<LoteEditForm>();
  const especieSeleccionadaId = createForm.watch("especie_id");
  const especieSeleccionada = especies.find((row) => row.id === Number(especieSeleccionadaId));

  const createMut = useMutation({
    mutationFn: (data: LoteCreate) => createLote(data),
    onSuccess: async () => {
      setCreating(false);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["lotes"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: LoteUpdate }) => updateLote(id, data),
    onSuccess: async () => {
      setEditing(null);
      setFormError(null);
      await queryClient.invalidateQueries({ queryKey: ["lotes"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    createForm.reset({
      codigo: "",
      estanque_id: 0,
      especie_id: 0,
      etapa_productiva_id: 0,
      estado_id: 0,
      fecha_siembra: new Date().toISOString().slice(0, 10),
      fecha_cierre: "",
      cantidad_sembrada: "",
      peso_inicial_promedio_g: "1.0",
      observaciones: "",
    });
    setCreating(true);
  }

  function openEdit(row: Lote) {
    setFormError(null);
    editForm.reset({
      etapa_productiva_id: row.etapa_productiva_id,
      estado_id: row.estado_id,
      fecha_cierre: row.fecha_cierre ?? "",
      observaciones: row.observaciones ?? "",
    });
    setEditing(row);
  }

  function onCreate(values: LoteCreateForm) {
    if (!catalogoAltaOk) {
      setFormError("Registre al menos una especie activa, una etapa, un estado de lote y un estanque.");
      return;
    }
    const peso = values.peso_inicial_promedio_g.trim();
    const pesoNum = peso === "" ? null : Number(peso);
    if (pesoNum != null && pesoNum <= 0) {
      setFormError("El peso inicial debe ser mayor que 0.");
      return;
    }
    createMut.mutate({
      codigo: values.codigo.trim(),
      estanque_id: Number(values.estanque_id),
      especie_id: Number(values.especie_id),
      etapa_productiva_id: Number(values.etapa_productiva_id),
      estado_id: Number(values.estado_id),
      fecha_siembra: values.fecha_siembra,
      fecha_cierre: values.fecha_cierre || null,
      cantidad_sembrada: Number(values.cantidad_sembrada),
      peso_inicial_promedio_g: pesoNum,
      observaciones: values.observaciones.trim() || null,
    });
  }

  function onEdit(values: LoteEditForm) {
    if (!editing) return;
    updateMut.mutate({
      id: editing.id,
      data: {
        etapa_productiva_id: Number(values.etapa_productiva_id),
        estado_id: Number(values.estado_id),
        fecha_cierre: values.fecha_cierre || null,
        observaciones: values.observaciones.trim() || null,
      },
    });
  }

  const etapasEdicion = etapas;
  const estadosEdicion = estados;

  return (
    <div>
      <PageHeader
        title="Lotes"
        description="Ciclo productivo por estanque. Un estanque solo puede tener un lote ACTIVO (regla de PostgreSQL)."
        actions={
          puedeCrear ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Nuevo lote
            </button>
          ) : null
        }
      />

      {lotesQuery.isLoading ? <LoadingState label="Cargando lotes…" /> : null}
      {lotesQuery.isError ? (
        <div className="space-y-3">
          <ErrorAlert message={apiErrorMessage(lotesQuery.error)} />
          <button type="button" className="bf-btn-primary" onClick={() => void lotesQuery.refetch()}>
            Reintentar
          </button>
        </div>
      ) : null}

      {lotesQuery.data ? (
        <DataTable
          rows={lotesQuery.data}
          rowKey={(row) => row.id}
          empty="Sin lotes registrados."
          onRowClick={(row) => navigate(pathFichaEstanque(row.estanque_id, { loteId: row.id }))}
          columns={[
            { key: "codigo", header: "Código" },
            {
              key: "estanque",
              header: "Estanque",
              render: (row) => (
                <span
                  className="font-medium text-[var(--bf-accent)] hover:underline"
                  onClick={(event) => {
                    event.stopPropagation();
                    navigate(pathFichaEstanque(row.estanque_id, { loteId: row.id }));
                  }}
                >
                  {estanques.get(row.estanque_id)?.codigo ?? `#${row.estanque_id}`}
                </span>
              ),
            },
            {
              key: "especie",
              header: "Especie",
              render: (row) => row.especie.nombre_comun,
            },
            {
              key: "etapa",
              header: "Etapa",
              render: (row) => row.etapa_productiva.nombre,
            },
            {
              key: "estado",
              header: "Estado",
              render: (row) => (
                <StatusBadge
                  label={row.estado.nombre}
                  tone={row.estado.nombre === "ACTIVO" ? "ok" : "neutral"}
                />
              ),
            },
            {
              key: "siembra",
              header: "Siembra",
              render: (row) => formatDate(row.fecha_siembra),
            },
            {
              key: "cantidad",
              header: "Sembrados",
              render: (row) => formatNumber(row.cantidad_sembrada),
            },
            {
              key: "acciones",
              header: "",
              render: (row) =>
                puedeEditar ? (
                  <button
                    type="button"
                    className="bf-btn-secondary !py-1 text-xs"
                    onClick={(event) => {
                      event.stopPropagation();
                      openEdit(row);
                    }}
                  >
                    Editar
                  </button>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      ) : null}

      <Modal
        open={creating}
        title="Nuevo lote"
        onClose={() => {
          setCreating(false);
          setFormError(null);
        }}
      >
        {!catalogoAltaOk ? (
          <ErrorAlert message="Para crear un lote hacen falta especies activas, etapas productivas, estados de lote y al menos un estanque. El administrador registra las especies en Catálogos → Producción." />
        ) : (
          <form className="space-y-3" onSubmit={createForm.handleSubmit(onCreate)}>
            {formError ? <ErrorAlert message={formError} /> : null}
            <Field label="Código">
              <input className="bf-input" {...createForm.register("codigo", { required: true })} />
            </Field>
            <Field label="Estanque">
              <select className="bf-input" {...createForm.register("estanque_id", { valueAsNumber: true, required: true })}>
                <option value="">Seleccione un estanque</option>
                {(estanquesQuery.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo} · {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Especie">
              <select className="bf-input" {...createForm.register("especie_id", { valueAsNumber: true, required: true })}>
                <option value="">Seleccione una especie</option>
                {especies.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre_comun}
                  </option>
                ))}
              </select>
            </Field>
            {especieSeleccionada ? (
              <p className="text-xs text-[var(--bf-muted)]">
                Referencias de {especieSeleccionada.nombre_comun}:{" "}
                {especieSeleccionada.n_referencias_produccion > 0
                  ? `✓ Producción: ${formatNumber(especieSeleccionada.n_referencias_produccion)}`
                  : "⚠ Producción: sin referencias"}
                {" · "}
                {especieSeleccionada.n_referencias_agua > 0
                  ? `✓ Agua: ${formatNumber(especieSeleccionada.n_referencias_agua)}`
                  : "⚠ Agua: sin referencias"}
                {" · "}
                ⚠ Biofloc: sin referencias. La siembra no se bloquea por falta de referencias.
              </p>
            ) : null}
            <Field label="Etapa">
              <select className="bf-input" {...createForm.register("etapa_productiva_id", { valueAsNumber: true, required: true })}>
                <option value="">Seleccione una etapa</option>
                {etapasActivas.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Estado">
              <select className="bf-input" {...createForm.register("estado_id", { valueAsNumber: true, required: true })}>
                <option value="">Seleccione un estado</option>
                {estadosActivos.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <p className="text-xs text-[var(--bf-muted)]">
              La especie sale del catálogo activo. El administrador define las referencias en Catálogos.
            </p>
            <Field label="Fecha de siembra">
              <input type="date" className="bf-input" {...createForm.register("fecha_siembra", { required: true })} />
            </Field>
            <Field label="Fecha de cierre (opcional)">
              <input type="date" className="bf-input" {...createForm.register("fecha_cierre")} />
            </Field>
            <Field label="Cantidad sembrada">
              <input
                type="number"
                min="1"
                className="bf-input"
                {...createForm.register("cantidad_sembrada", { required: true, valueAsNumber: true })}
              />
            </Field>
            <Field label="Peso inicial promedio (g)">
              <input type="number" step="any" min="0.01" className="bf-input" placeholder="1.0" {...createForm.register("peso_inicial_promedio_g", { required: true })} />
              <p className="mt-1 text-xs text-[var(--bf-muted)]">Peso promedio de los alevinos al momento de la siembra. Típicamente ~1 g.</p>
            </Field>
            <Field label="Observaciones">
              <textarea className="bf-input min-h-20" {...createForm.register("observaciones")} />
            </Field>
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
        <form className="space-y-3" onSubmit={editForm.handleSubmit(onEdit)}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <p className="text-xs text-[var(--bf-muted)]">
            PUT solo acepta etapa, estado, fecha de cierre y observaciones.
          </p>
          <Field label="Etapa">
            <select className="bf-input" {...editForm.register("etapa_productiva_id", { valueAsNumber: true })}>
              {etapasEdicion.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...editForm.register("estado_id", { valueAsNumber: true })}>
              {estadosEdicion.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Fecha de cierre">
            <input type="date" className="bf-input" {...editForm.register("fecha_cierre")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...editForm.register("observaciones")} />
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={updateMut.isPending}>
            {updateMut.isPending ? "Guardando…" : "Guardar"}
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
