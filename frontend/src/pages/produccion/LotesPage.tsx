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
import { createLote, listEstanques, listLotes, updateLote } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDate, formatNumber, uniqueById } from "../../utils/format";
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

  const estanques = useMemo(() => {
    const map = new Map((estanquesQuery.data ?? []).map((row) => [row.id, row]));
    return map;
  }, [estanquesQuery.data]);

  const especies = useMemo(
    () => uniqueById((lotesQuery.data ?? []).map((row) => row.especie)),
    [lotesQuery.data],
  );
  const etapas = useMemo(
    () => uniqueById((lotesQuery.data ?? []).map((row) => row.etapa_productiva)),
    [lotesQuery.data],
  );
  const estados = useMemo(
    () => uniqueById((lotesQuery.data ?? []).map((row) => row.estado)),
    [lotesQuery.data],
  );

  const catalogoAltaOk =
    especies.length > 0 && etapas.length > 0 && estados.length > 0 && (estanquesQuery.data?.length ?? 0) > 0;

  const createForm = useForm<LoteCreateForm>();
  const editForm = useForm<LoteEditForm>();

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
      estanque_id: estanquesQuery.data?.[0]?.id ?? 0,
      especie_id: especies[0]?.id ?? 0,
      etapa_productiva_id: etapas[0]?.id ?? 0,
      estado_id: estados[0]?.id ?? 0,
      fecha_siembra: new Date().toISOString().slice(0, 10),
      fecha_cierre: "",
      cantidad_sembrada: "",
      peso_inicial_promedio_g: "",
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
      setFormError("El formulario de alta requiere un catálogo que la API no expone.");
      return;
    }
    const peso = values.peso_inicial_promedio_g.trim();
    createMut.mutate({
      codigo: values.codigo.trim(),
      estanque_id: Number(values.estanque_id),
      especie_id: Number(values.especie_id),
      etapa_productiva_id: Number(values.etapa_productiva_id),
      estado_id: Number(values.estado_id),
      fecha_siembra: values.fecha_siembra,
      fecha_cierre: values.fecha_cierre || null,
      cantidad_sembrada: Number(values.cantidad_sembrada),
      peso_inicial_promedio_g: peso === "" ? null : Number(peso),
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

  const etapasEdicion = editing ? uniqueById([...etapas, editing.etapa_productiva]) : etapas;
  const estadosEdicion = editing ? uniqueById([...estados, editing.estado]) : estados;

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
          empty="No hay lotes para mostrar."
          onRowClick={(row) => navigate(`/produccion/lotes/${row.id}`)}
          columns={[
            { key: "codigo", header: "Código" },
            {
              key: "estanque",
              header: "Estanque",
              render: (row) => estanques.get(row.estanque_id)?.codigo ?? `#${row.estanque_id}`,
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
          <ErrorAlert message="El formulario de alta requiere un catálogo que la API no expone. No hay GET de especies, etapas_productivas ni estados_lote; solo se reutilizan valores anidados de lotes ya existentes, más estanques listados." />
        ) : (
          <form className="space-y-3" onSubmit={createForm.handleSubmit(onCreate)}>
            {formError ? <ErrorAlert message={formError} /> : null}
            <Field label="Código">
              <input className="bf-input" {...createForm.register("codigo", { required: true })} />
            </Field>
            <Field label="Estanque">
              <select className="bf-input" {...createForm.register("estanque_id", { valueAsNumber: true })}>
                {(estanquesQuery.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.codigo} · {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Especie">
              <select className="bf-input" {...createForm.register("especie_id", { valueAsNumber: true })}>
                {especies.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre_comun}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Etapa">
              <select className="bf-input" {...createForm.register("etapa_productiva_id", { valueAsNumber: true })}>
                {etapas.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Estado">
              <select className="bf-input" {...createForm.register("estado_id", { valueAsNumber: true })}>
                {estados.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.nombre}
                  </option>
                ))}
              </select>
            </Field>
            <p className="text-xs text-[var(--bf-muted)]">
              Especie, etapa y estado salen de lotes ya listados. La API no expone esos catálogos.
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
            <Field label="Peso inicial promedio en gramos (opcional)">
              <input type="number" step="any" min="0" className="bf-input" {...createForm.register("peso_inicial_promedio_g")} />
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
