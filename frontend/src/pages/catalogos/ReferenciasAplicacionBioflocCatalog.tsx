import { useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { StatusBadge } from "../../components/StatusBadge";
import {
  createReferenciaAplicacionBiofloc,
  listReferenciasAplicacionBiofloc,
  updateReferenciaAplicacionBiofloc,
} from "../../api/catalogs";
import { listEspecies } from "../../api/production";
import { listProductosActivos } from "../../api/operations";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, parseDecimalInput } from "../../utils/format";
import type { ReferenciaAplicacionBiofloc } from "../../types/operations";

const FASES = ["Inicio", "Levante", "Engorde"] as const;

type FormValues = {
  especie_id: number | "";
  semana: number | "";
  fase: string;
  producto_id: number | "";
  cantidad_referencia: string;
  unidad: string;
  base_peces: string;
  biomasa_objetivo_kg: string;
  observaciones: string;
  activo: "true" | "false";
};

export function ReferenciasAplicacionBioflocCatalog({ canWrite }: { canWrite: boolean }) {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ReferenciaAplicacionBiofloc | null>(null);
  const [especieFiltro, setEspecieFiltro] = useState<number | "todas">("todas");
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<FormValues>();

  const refsQuery = useQuery({
    queryKey: ["referencias-aplicacion-biofloc", "catalog"],
    queryFn: () => listReferenciasAplicacionBiofloc({ solo_activos: false }),
  });
  const especiesQuery = useQuery({
    queryKey: ["especies", "catalog"],
    queryFn: () => listEspecies(false),
  });
  const productosQuery = useQuery({
    queryKey: ["productos-activos", "catalog-biofloc"],
    queryFn: listProductosActivos,
  });

  const especies = useMemo(
    () => new Map((especiesQuery.data ?? []).map((row) => [row.id, row.nombre_comun])),
    [especiesQuery.data],
  );
  const productos = useMemo(
    () => new Map((productosQuery.data ?? []).map((row) => [row.id, row])),
    [productosQuery.data],
  );
  const filas = useMemo(() => {
    const rows = refsQuery.data ?? [];
    return especieFiltro === "todas" ? rows : rows.filter((row) => row.especie_id === especieFiltro);
  }, [refsQuery.data, especieFiltro]);

  const createMut = useMutation({
    mutationFn: createReferenciaAplicacionBiofloc,
    onSuccess: async () => {
      setCreating(false);
      await queryClient.invalidateQueries({ queryKey: ["referencias-aplicacion-biofloc"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateReferenciaAplicacionBiofloc>[1] }) =>
      updateReferenciaAplicacionBiofloc(id, data),
    onSuccess: async () => {
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["referencias-aplicacion-biofloc"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      especie_id: "",
      semana: "",
      fase: "",
      producto_id: "",
      cantidad_referencia: "",
      unidad: "kg",
      base_peces: "1100",
      biomasa_objetivo_kg: "",
      observaciones: "",
      activo: "true",
    });
    setCreating(true);
  }

  function openEdit(row: ReferenciaAplicacionBiofloc) {
    setFormError(null);
    setEditing(row);
    form.reset({
      especie_id: row.especie_id,
      semana: row.semana,
      fase: row.fase,
      producto_id: row.producto_id,
      cantidad_referencia: String(row.cantidad_referencia),
      unidad: row.unidad,
      base_peces: String(row.base_peces),
      biomasa_objetivo_kg: row.biomasa_objetivo_kg == null ? "" : String(row.biomasa_objetivo_kg),
      observaciones: row.observaciones ?? "",
      activo: row.activo ? "true" : "false",
    });
  }

  function submit(values: FormValues) {
    setFormError(null);
    const payload = {
      especie_id: Number(values.especie_id),
      semana: Number(values.semana),
      fase: values.fase as "Inicio" | "Levante" | "Engorde",
      producto_id: Number(values.producto_id),
      cantidad_referencia: parseDecimalInput(values.cantidad_referencia) ?? 0,
      unidad: values.unidad.trim() || "kg",
      base_peces: Number(values.base_peces),
      biomasa_objetivo_kg: parseDecimalInput(values.biomasa_objetivo_kg),
      observaciones: values.observaciones.trim() || null,
      activo: values.activo === "true",
    };
    if (editing) {
      updateMut.mutate({
        id: editing.id,
        data: {
          cantidad_referencia: payload.cantidad_referencia,
          unidad: payload.unidad,
          base_peces: payload.base_peces,
          biomasa_objetivo_kg: payload.biomasa_objetivo_kg,
          observaciones: payload.observaciones,
          activo: payload.activo,
        },
      });
    } else {
      createMut.mutate(payload);
    }
  }

  const pending = createMut.isPending || updateMut.isPending;
  const loading = refsQuery.isLoading || especiesQuery.isLoading || productosQuery.isLoading;

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Referencia semanal de Biofloc</h2>
          <p className="mt-1 max-w-4xl text-sm text-[var(--bf-muted)]">
            Melaza, probiótico, bicarbonato y sal marina por semana y fase. La referencia actual está basada en 1.100 peces y 400 kg objetivo; es presupuestal y debe ajustarse con las mediciones del sistema y la ficha técnica del producto.
          </p>
        </div>
        {canWrite ? (
          <button type="button" className="bf-btn-primary" onClick={openCreate}>
            Nueva referencia
          </button>
        ) : null}
      </div>

      <label className="mb-4 block max-w-sm text-sm">
        <span className="mb-1 block font-medium text-[var(--bf-ink)]">Ver por especie</span>
        <select
          className="bf-input"
          value={especieFiltro === "todas" ? "todas" : String(especieFiltro)}
          onChange={(e) => setEspecieFiltro(e.target.value === "todas" ? "todas" : Number(e.target.value))}
        >
          <option value="todas">Todas</option>
          {(especiesQuery.data ?? []).map((row) => (
            <option key={row.id} value={row.id}>{row.nombre_comun}</option>
          ))}
        </select>
      </label>

      {loading ? <LoadingState /> : null}
      {refsQuery.isError ? <ErrorAlert message={apiErrorMessage(refsQuery.error)} /> : null}

      {filas.length > 0 ? (
        <DataTable
          rows={filas}
          rowKey={(row) => row.id}
          empty="Sin referencias Biofloc."
          columns={[
            { key: "especie", header: "Especie", render: (row) => especies.get(row.especie_id) ?? `#${row.especie_id}` },
            { key: "semana", header: "Semana", render: (row) => row.semana },
            { key: "fase", header: "Fase", render: (row) => row.fase },
            { key: "producto", header: "Insumo", render: (row) => productos.get(row.producto_id)?.nombre ?? `#${row.producto_id}` },
            { key: "cantidad", header: "Cantidad/semana", render: (row) => `${formatNumber(row.cantidad_referencia, { maximumFractionDigits: 4 })} ${row.unidad}` },
            { key: "base", header: "Base", render: (row) => `${formatNumber(row.base_peces)} peces` },
            { key: "biomasa", header: "Biomasa obj.", render: (row) => row.biomasa_objetivo_kg == null ? "N/D" : `${formatNumber(row.biomasa_objetivo_kg, { maximumFractionDigits: 3 })} kg` },
            { key: "activo", header: "Estado", render: (row) => <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} /> },
            ...(canWrite ? [{
              key: "acciones",
              header: "",
              className: "text-right",
              render: (row: ReferenciaAplicacionBiofloc) => (
                <button type="button" className="bf-btn-secondary !px-2 !py-1 text-xs" onClick={() => openEdit(row)}>Editar</button>
              ),
            }] : []),
          ] satisfies DataTableColumn<ReferenciaAplicacionBiofloc>[]}
        />
      ) : !loading ? (
        <p className="rounded-lg border border-dashed border-[var(--bf-border)] px-4 py-6 text-center text-sm text-[var(--bf-muted)]">
          Sin referencias semanales Biofloc.
        </p>
      ) : null}

      <Modal open={creating || Boolean(editing)} title={editing ? "Editar referencia semanal Biofloc" : "Nueva referencia semanal Biofloc"} onClose={() => { setCreating(false); setEditing(null); }}>
        <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Especie">
            <select className="bf-input" disabled={Boolean(editing)} {...form.register("especie_id", { required: true })}>
              <option value="">Seleccione una especie</option>
              {(especiesQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.nombre_comun}</option>)}
            </select>
          </Field>
          <Field label="Semana">
            <input type="number" min="1" className="bf-input" disabled={Boolean(editing)} {...form.register("semana", { required: true })} />
          </Field>
          <Field label="Fase">
            <select className="bf-input" disabled={Boolean(editing)} {...form.register("fase", { required: true })}>
              <option value="">Seleccione una fase</option>
              {FASES.map((fase) => <option key={fase} value={fase}>{fase}</option>)}
            </select>
          </Field>
          <Field label="Insumo Biofloc">
            <select className="bf-input" disabled={Boolean(editing)} {...form.register("producto_id", { required: true })}>
              <option value="">Seleccione un insumo</option>
              {(productosQuery.data ?? []).filter((p) => p.codigo.startsWith("BF-")).map((row) => (
                <option key={row.id} value={row.id}>{row.nombre} ({row.codigo})</option>
              ))}
            </select>
          </Field>
          <Field label="Cantidad de referencia por semana">
            <input type="number" min="0" step="any" className="bf-input" {...form.register("cantidad_referencia", { required: true })} />
          </Field>
          <Field label="Unidad">
            <input className="bf-input" {...form.register("unidad", { required: true })} />
          </Field>
          <Field label="Base de peces">
            <input type="number" min="1" className="bf-input" {...form.register("base_peces", { required: true })} />
          </Field>
          <Field label="Biomasa objetivo de la semana (kg)">
            <input type="number" min="0" step="any" className="bf-input" {...form.register("biomasa_objetivo_kg")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <Field label="Estado">
            <select className="bf-input" {...form.register("activo")}>
              <option value="true">Activo</option>
              <option value="false">Inactivo</option>
            </select>
          </Field>
          <button type="submit" className="bf-btn-primary" disabled={pending}>{pending ? "Guardando…" : "Guardar"}</button>
        </form>
      </Modal>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-sm"><span className="mb-1 block font-medium text-[var(--bf-ink)]">{label}</span>{children}</label>;
}
