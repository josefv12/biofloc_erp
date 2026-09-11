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
import { createGasto, listCategoriasGasto, listGastos } from "../../api/finance";
import { listEstanques, listLotes } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Gasto, GastoCreate } from "../../types/finance";

type GastoForm = {
  fecha: string;
  categoria_id: number;
  destino: "lote" | "estanque" | "general";
  lote_id: string;
  estanque_id: string;
  descripcion: string;
  valor: number | "";
  proveedor: string;
  observaciones: string;
};

function todayDateInput(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function GastosPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const loteId = Number(params.get("lote_id") ?? "") || undefined;
  const estanqueId = Number(params.get("estanque_id") ?? "") || undefined;
  const categoriaId = Number(params.get("categoria_id") ?? "") || undefined;
  const fechaDesde = params.get("fecha_desde") ?? "";
  const fechaHasta = params.get("fecha_hasta") ?? "";
  const [open, setOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeRegistrar = can(user?.rol, "registrarGasto");

  const gastosQuery = useQuery({
    queryKey: ["gastos", loteId, estanqueId, categoriaId, fechaDesde, fechaHasta],
    queryFn: () =>
      listGastos({
        loteId,
        estanqueId,
        categoriaId,
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
      }),
  });
  const categoriasQuery = useQuery({
    queryKey: ["categorias-gasto"],
    queryFn: () => listCategoriasGasto(false),
  });
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const estanquesQuery = useQuery({ queryKey: ["estanques"], queryFn: () => listEstanques() });
  const categorias = useMemo(
    () => new Map((categoriasQuery.data ?? []).map((row) => [row.id, row])),
    [categoriasQuery.data],
  );
  const lotes = useMemo(() => new Map((lotesQuery.data ?? []).map((row) => [row.id, row])), [lotesQuery.data]);
  const estanques = useMemo(
    () => new Map((estanquesQuery.data ?? []).map((row) => [row.id, row])),
    [estanquesQuery.data],
  );
  const form = useForm<GastoForm>();
  const destino = form.watch("destino") ?? "general";
  const mutation = useMutation({
    mutationFn: (data: GastoCreate) => createGasto(data),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["gastos"] });
      await queryClient.invalidateQueries({ queryKey: ["analisis-lote"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-finanzas"] });
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function openCreate() {
    setFormError(null);
    form.reset({
      fecha: todayDateInput(),
      categoria_id: categoriasQuery.data?.[0]?.id ?? 0,
      destino: loteId ? "lote" : estanqueId ? "estanque" : "general",
      lote_id: loteId ? String(loteId) : "",
      estanque_id: estanqueId ? String(estanqueId) : "",
      descripcion: "",
      valor: "",
      proveedor: "",
      observaciones: "",
    });
    setOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Costos"
        description="Registra costos directos del lote, costos del estanque o gastos generales."
        actions={
          puedeRegistrar ? (
            <button type="button" className="bf-btn-primary" onClick={openCreate}>
              Registrar costo
            </button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Desde</span>
          <input type="date" className="bf-input" value={fechaDesde} onChange={(e) => setParam("fecha_desde", e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Hasta</span>
          <input type="date" className="bf-input" value={fechaHasta} onChange={(e) => setParam("fecha_hasta", e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Categoría</span>
          <select className="bf-input" value={categoriaId ?? ""} onChange={(e) => setParam("categoria_id", e.target.value)}>
            <option value="">Todas</option>
            {(categoriasQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>{row.nombre}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Lote</span>
          <select className="bf-input" value={loteId ?? ""} onChange={(e) => setParam("lote_id", e.target.value)}>
            <option value="">Todos</option>
            {(lotesQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>{row.codigo}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--bf-muted)]">Estanque</span>
          <select className="bf-input" value={estanqueId ?? ""} onChange={(e) => setParam("estanque_id", e.target.value)}>
            <option value="">Todos</option>
            {(estanquesQuery.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>{row.codigo}</option>
            ))}
          </select>
        </label>
      </div>

      {gastosQuery.isLoading ? <LoadingState /> : null}
      {gastosQuery.isError ? <ErrorAlert message={apiErrorMessage(gastosQuery.error)} /> : null}
      {gastosQuery.data ? (
        <DataTable
          rows={gastosQuery.data}
          rowKey={(row: Gasto) => row.id}
          empty="No hay costos registrados."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDate(row.fecha) },
            { key: "cat", header: "Categoría", render: (row) => categorias.get(row.categoria_id)?.nombre ?? `#${row.categoria_id}` },
            { key: "desc", header: "Descripción", render: (row) => row.descripcion },
            { key: "valor", header: "Valor", render: (row) => formatCop(row.valor) },
            { key: "proveedor", header: "Proveedor", render: (row) => row.proveedor || "—" },
            {
              key: "destino",
              header: "Destino",
              render: (row) => row.lote_id != null
                ? <Link to={`/produccion/lotes/${row.lote_id}`} className="text-[var(--bf-accent)]">Lote {lotes.get(row.lote_id)?.codigo ?? `#${row.lote_id}`}</Link>
                : row.estanque_id != null
                  ? `Estanque ${estanques.get(row.estanque_id)?.codigo ?? `#${row.estanque_id}`}`
                  : "General",
            },
            { key: "obs", header: "Observaciones", render: (row) => row.observaciones || "—" },
          ]}
        />
      ) : null}

      <Modal open={open} title="Registrar costo" onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={form.handleSubmit((values) => {
            const lote = values.lote_id.trim();
            const estanque = values.estanque_id.trim();
            mutation.mutate({
              fecha: values.fecha,
              categoria_id: Number(values.categoria_id),
              lote_id: values.destino === "lote" && lote ? Number(lote) : null,
              estanque_id: values.destino === "estanque" && estanque ? Number(estanque) : null,
              descripcion: values.descripcion.trim(),
              valor: Number(values.valor),
              proveedor: values.proveedor.trim() || null,
              observaciones: values.observaciones.trim() || null,
            });
          })}
        >
          {formError ? <ErrorAlert message={formError} /> : null}
          <Field label="Fecha">
            <input type="date" className="bf-input" {...form.register("fecha", { required: true })} />
          </Field>
          <Field label="Categoría">
            <select className="bf-input" {...form.register("categoria_id", { valueAsNumber: true })}>
              {(categoriasQuery.data ?? []).filter((row) => row.activo).map((row) => (
                <option key={row.id} value={row.id}>{row.nombre}</option>
              ))}
            </select>
          </Field>
          <Field label="Destino del costo">
            <select className="bf-input" {...form.register("destino")}>
              <option value="lote">Lote</option>
              <option value="estanque">Estanque</option>
              <option value="general">General</option>
            </select>
          </Field>
          {destino === "lote" ? (
            <Field label="Lote">
              <select className="bf-input" {...form.register("lote_id", { required: true })}>
                <option value="">Selecciona un lote</option>
                {(lotesQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.codigo}</option>)}
              </select>
            </Field>
          ) : null}
          {destino === "estanque" ? (
            <Field label="Estanque">
              <select className="bf-input" {...form.register("estanque_id", { required: true })}>
                <option value="">Selecciona un estanque</option>
                {(estanquesQuery.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.codigo}</option>)}
              </select>
            </Field>
          ) : null}
          <Field label="Descripción">
            <input className="bf-input" {...form.register("descripcion", { required: true })} placeholder="Ej. compra de alevinos" />
          </Field>
          <Field label="Valor">
            <input type="number" step="any" min="0.01" className="bf-input" {...form.register("valor", { valueAsNumber: true })} />
          </Field>
          <Field label="Proveedor (opcional)">
            <input className="bf-input" {...form.register("proveedor")} />
          </Field>
          <Field label="Observaciones">
            <textarea className="bf-input min-h-20" {...form.register("observaciones")} />
          </Field>
          <p className="text-xs text-[var(--bf-muted)]">
            El alimento suministrado a un lote se costea automáticamente desde el consumo de inventario; no lo registres otra vez como gasto.
          </p>
          <button
            type="submit"
            className="bf-btn-primary"
            disabled={mutation.isPending || (categoriasQuery.data ?? []).filter((row) => row.activo).length === 0}
          >
            {mutation.isPending ? "Guardando…" : "Registrar"}
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
