import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuth } from "../../auth/AuthProvider";
import { createProducto, listAlertasStockBajo, listCategoriasInventario, listProductos, listProductosStock, updateProducto } from "../../api/inventory";
import { listUnidades } from "../../api/operations";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, etiquetaProducto } from "../../utils/format";
import { can } from "../../utils/rbac";
import { cantidadDesdePresentacion, cantidadParaPresentacion } from "../../utils/unidades";
import type { Producto, ProductoCreate, ProductoUpdate } from "../../types/inventory";

type ProductoForm = {
  codigo: string;
  nombre: string;
  categoria_id: number;
  unidad_id: number;
  unidad_comercial_id: number;
  factor_conversion: number;
  stock_minimo: number;
  activo: boolean;
};

function toneClasificacion(value: string | undefined) {
  if (value === "SIN_STOCK") return "danger" as const;
  if (value === "STOCK_BAJO") return "warn" as const;
  if (value === "NORMAL") return "ok" as const;
  return "neutral" as const;
}

export function InventarioPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Producto | null>(null);
  const [toToggle, setToToggle] = useState<Producto | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const puedeEscribir = can(user?.rol, "escribirProducto");

  const productosQuery = useQuery({ queryKey: ["productos", { soloActivos: !incluirInactivos }], queryFn: () => listProductos({ soloActivos: !incluirInactivos }) });
  const stockQuery = useQuery({ queryKey: ["productos-stock"], queryFn: listProductosStock });
  const alertasQuery = useQuery({ queryKey: ["alertas-stock-bajo", incluirInactivos], queryFn: () => listAlertasStockBajo({ soloActivos: !incluirInactivos, incluirNormal: true }) });
  const stockBajoQuery = useQuery({ queryKey: ["alertas-stock-bajo-seccion"], queryFn: () => listAlertasStockBajo({ soloActivos: true, incluirNormal: false }) });
  const categoriasQuery = useQuery({ queryKey: ["categorias-inventario"], queryFn: () => listCategoriasInventario(false) });
  const unidadesQuery = useQuery({ queryKey: ["unidades"], queryFn: listUnidades });

  const categorias = useMemo(() => new Map((categoriasQuery.data ?? []).map((row) => [row.id, row])), [categoriasQuery.data]);
  const unidades = useMemo(() => new Map((unidadesQuery.data ?? []).map((row) => [row.id, row])), [unidadesQuery.data]);
  const stockMap = useMemo(() => new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row])), [stockQuery.data]);
  const clasificacionMap = useMemo(() => new Map((alertasQuery.data ?? []).map((row) => [row.producto_id, row])), [alertasQuery.data]);
  const productosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const rows = productosQuery.data ?? [];
    if (!q) return rows;
    return rows.filter((row) => row.nombre.toLowerCase().includes(q) || row.codigo.toLowerCase().includes(q));
  }, [productosQuery.data, busqueda]);

  const form = useForm<ProductoForm>();

  const createMut = useMutation({
    mutationFn: (data: ProductoCreate) => createProducto(data),
    onSuccess: async () => { setCreating(false); setFormError(null); await invalidateInventario(queryClient); },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductoUpdate }) => updateProducto(id, data),
    onSuccess: async () => { setEditing(null); setToToggle(null); setFormError(null); await invalidateInventario(queryClient); },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    const unidadInicial = unidadesQuery.data?.[0]?.id ?? 0;
    form.reset({ codigo: "", nombre: "", categoria_id: categoriasQuery.data?.[0]?.id ?? 0, unidad_id: unidadInicial, unidad_comercial_id: unidadInicial, factor_conversion: 1, stock_minimo: 0, activo: true });
    setCreating(true);
  }

  function openEdit(producto: Producto) {
    setFormError(null);
    const factor = Number(producto.factor_conversion) > 0 ? Number(producto.factor_conversion) : 1;
    const unidadInterna = unidades.get(producto.unidad_id)?.simbolo ?? "";
    form.reset({
      codigo: producto.codigo,
      nombre: producto.nombre,
      categoria_id: producto.categoria_id,
      unidad_id: producto.unidad_id,
      unidad_comercial_id: producto.unidad_comercial_id,
      factor_conversion: factor,
      stock_minimo: cantidadParaPresentacion(producto.stock_minimo, unidadInterna, factor),
      activo: producto.activo,
    });
    setEditing(producto);
  }

  const loading = productosQuery.isLoading || stockQuery.isLoading || alertasQuery.isLoading;
  const error = productosQuery.error ?? stockQuery.error ?? alertasQuery.error;

  return (
    <div>
      <PageHeader title="Inventario" description="Productos y stock por unidad. No se suman kg con litros. Stock y clasificación salen del API, no se calculan aquí." actions={<div className="flex flex-wrap items-center gap-2"><label className="flex items-center gap-2 text-sm text-[var(--bf-muted)]"><input type="checkbox" checked={incluirInactivos} onChange={(event) => setIncluirInactivos(event.target.checked)} />Incluir inactivos</label>{puedeEscribir ? <button type="button" className="bf-btn-primary" onClick={openCreate}>Nuevo producto</button> : null}</div>} />

      <section className="mb-6 rounded-xl border border-[var(--bf-border)] bg-white p-4">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2"><div><h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Stock bajo</h2><p className="text-sm text-[var(--bf-muted)]">Alertas de inventario del API. No son las alarmas del sistema de la granja.</p></div><Link to="/inventario/movimientos" className="bf-btn-secondary">Ver movimientos</Link></div>
        {stockBajoQuery.isLoading ? <LoadingState /> : null}
        {stockBajoQuery.isError ? <ErrorAlert message={apiErrorMessage(stockBajoQuery.error)} /> : null}
        {stockBajoQuery.data ? <DataTable rows={stockBajoQuery.data} rowKey={(row) => row.producto_id} empty="No hay productos en SIN_STOCK ni STOCK_BAJO." columns={[
          { key: "codigo", header: "Producto", render: (row) => etiquetaProducto(row.nombre, row.codigo) },
          { key: "stock", header: "Stock", render: (row) => { const stock = stockMap.get(row.producto_id); const factor = stock?.factor_conversion ?? 1; const unidadComercial = stock?.unidad_comercial ?? row.unidad; return `${formatNumber(cantidadParaPresentacion(row.stock_actual, row.unidad, factor), { maximumFractionDigits: 3 })} ${unidadComercial}`; } },
          { key: "min", header: "Stock mínimo", render: (row) => { const stock = stockMap.get(row.producto_id); const factor = stock?.factor_conversion ?? 1; const unidadComercial = stock?.unidad_comercial ?? row.unidad; return `${formatNumber(cantidadParaPresentacion(row.stock_minimo, row.unidad, factor), { maximumFractionDigits: 3 })} ${unidadComercial}`; } },
          { key: "unidad", header: "Unidad comercial", render: (row) => stockMap.get(row.producto_id)?.unidad_comercial ?? row.unidad },
          { key: "clasif", header: "Clasificación", render: (row) => <StatusBadge label={row.clasificacion} tone={toneClasificacion(row.clasificacion)} /> },
        ]} /> : null}
      </section>

      {loading ? <LoadingState label="Cargando productos…" /> : null}
      {error ? <ErrorAlert message={apiErrorMessage(error)} /> : null}
      {productosQuery.data ? <div className="mb-3"><label className="text-sm"><span className="mb-1 block text-[var(--bf-muted)]">Buscar por nombre</span><input className="bf-input max-w-md" value={busqueda} placeholder="Buscar producto…" onChange={(event) => setBusqueda(event.target.value)} /></label></div> : null}

      {productosQuery.data ? <DataTable rows={productosFiltrados} rowKey={(row) => row.id} empty="No hay productos." columns={[
        { key: "codigo", header: "Código", render: (row) => row.codigo },
        { key: "nombre", header: "Nombre", render: (row) => row.nombre },
        { key: "cat", header: "Categoría", render: (row) => categorias.get(row.categoria_id)?.nombre ?? `#${row.categoria_id}` },
        { key: "unidad", header: "Unidades", render: (row) => { const interna = unidades.get(row.unidad_id)?.simbolo ?? `#${row.unidad_id}`; const comercial = unidades.get(row.unidad_comercial_id)?.simbolo ?? `#${row.unidad_comercial_id}`; return `${interna} → ${comercial}`; } },
        { key: "stock", header: "Stock", render: (row) => { const stock = stockMap.get(row.id); if (!stock) return "—"; return `${formatNumber(cantidadParaPresentacion(stock.stock_actual, stock.unidad, stock.factor_conversion), { maximumFractionDigits: 3 })} ${stock.unidad_comercial}`; } },
        { key: "min", header: "Stock mínimo", render: (row) => { const factor = Number(row.factor_conversion) > 0 ? Number(row.factor_conversion) : 1; const unidad = unidades.get(row.unidad_id)?.simbolo ?? ""; const comercial = unidades.get(row.unidad_comercial_id)?.simbolo ?? ""; return `${formatNumber(cantidadParaPresentacion(row.stock_minimo, unidad, factor), { maximumFractionDigits: 3 })} ${comercial}`; } },
        { key: "clasif", header: "Clasificación", render: (row) => { const alerta = clasificacionMap.get(row.id); return alerta ? <StatusBadge label={alerta.clasificacion} tone={toneClasificacion(alerta.clasificacion)} /> : "No hay clasificación disponible"; } },
        { key: "activo", header: "Activo", render: (row) => <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} /> },
        { key: "acciones", header: "", render: (row) => puedeEscribir ? <div className="flex justify-end gap-2"><button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => openEdit(row)}>Editar</button><button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => setToToggle(row)}>{row.activo ? "Desactivar" : "Activar"}</button></div> : null },
      ]} /> : null}

      <ProductoModal open={creating || Boolean(editing)} title={editing ? "Editar producto" : "Nuevo producto"} form={form} formError={formError} categorias={categoriasQuery.data ?? []} unidades={unidadesQuery.data ?? []} pending={createMut.isPending || updateMut.isPending} onClose={() => { setCreating(false); setEditing(null); }} onSubmit={(values) => {
        const factor = Number(values.factor_conversion);
        if (!Number.isFinite(factor) || factor <= 0) { setFormError("El factor de conversión debe ser mayor que cero."); return; }
        const unidadInterna = unidades.get(Number(values.unidad_id))?.simbolo ?? "";
        const stockMinimoInterno = cantidadDesdePresentacion(Number(values.stock_minimo), unidadInterna, factor);
        if (!Number.isFinite(stockMinimoInterno) || stockMinimoInterno < 0) { setFormError("El stock mínimo no es válido."); return; }
        const payload = { codigo: values.codigo.trim(), nombre: values.nombre.trim(), categoria_id: Number(values.categoria_id), unidad_id: Number(values.unidad_id), unidad_comercial_id: Number(values.unidad_comercial_id), factor_conversion: factor, stock_minimo: stockMinimoInterno, activo: values.activo };
        if (editing) updateMut.mutate({ id: editing.id, data: payload }); else createMut.mutate(payload);
      }} />

      <ConfirmDialog open={Boolean(toToggle)} title={toToggle?.activo ? "Desactivar producto" : "Activar producto"} description="El API no permite eliminar productos. Se cambia el campo activo." confirmLabel={toToggle?.activo ? "Desactivar" : "Activar"} onCancel={() => setToToggle(null)} onConfirm={() => { if (!toToggle) return; updateMut.mutate({ id: toToggle.id, data: { activo: !toToggle.activo } }); }} />
    </div>
  );
}

function invalidateInventario(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["productos"] }),
    queryClient.invalidateQueries({ queryKey: ["productos-stock"] }),
    queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo"] }),
    queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo-seccion"] }),
    queryClient.invalidateQueries({ queryKey: ["productos-activos"] }),
  ]);
}

function ProductoModal({ open, title, form, formError, categorias, unidades, pending, onClose, onSubmit }: { open: boolean; title: string; form: ReturnType<typeof useForm<ProductoForm>>; formError: string | null; categorias: { id: number; nombre: string }[]; unidades: { id: number; nombre: string; simbolo: string }[]; pending: boolean; onClose: () => void; onSubmit: (values: ProductoForm) => void; }) {
  return <Modal open={open} title={title} onClose={onClose}><form className="space-y-3" onSubmit={form.handleSubmit(onSubmit)}>
    {formError ? <ErrorAlert message={formError} /> : null}
    {categorias.length === 0 ? <ErrorAlert message="El formulario de alta requiere categorías que la API no devolvió." /> : null}
    <Field label="Código"><input className="bf-input" {...form.register("codigo", { required: true })} /></Field>
    <Field label="Nombre"><input className="bf-input" {...form.register("nombre", { required: true })} /></Field>
    <Field label="Categoría"><select className="bf-input" {...form.register("categoria_id", { valueAsNumber: true })}>{categorias.map((row) => <option key={row.id} value={row.id}>{row.nombre}</option>)}</select></Field>
    <Field label="Unidad interna de almacenamiento"><select className="bf-input" {...form.register("unidad_id", { valueAsNumber: true })}>{unidades.map((row) => <option key={row.id} value={row.id}>{row.nombre} ({row.simbolo})</option>)}</select><span className="mt-1 block text-xs text-[var(--bf-muted)]">Unidad en la que el sistema guarda inventario y movimientos.</span></Field>
    <Field label="Unidad comercial"><select className="bf-input" {...form.register("unidad_comercial_id", { valueAsNumber: true })}>{unidades.map((row) => <option key={row.id} value={row.id}>{row.nombre} ({row.simbolo})</option>)}</select><span className="mt-1 block text-xs text-[var(--bf-muted)]">Unidad que verá el usuario al comprar, alimentar y consultar stock.</span></Field>
    <Field label="Factor de conversión"><input type="number" step="any" min="0.000001" className="bf-input" {...form.register("factor_conversion", { valueAsNumber: true, min: 0.000001 })} /><span className="mt-1 block text-xs text-[var(--bf-muted)]">Cantidad de unidades internas que equivale a 1 unidad comercial. Ejemplo: g → kg = 1000.</span></Field>
    <Field label="Stock mínimo"><input type="number" step="any" min="0" className="bf-input" {...form.register("stock_minimo", { valueAsNumber: true })} /><span className="mt-1 block text-xs text-[var(--bf-muted)]">Se registra en la unidad comercial y el sistema lo convierte a la unidad interna.</span></Field>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("activo")} />Activo</label>
    <button type="submit" className="bf-btn-primary" disabled={pending || categorias.length === 0 || unidades.length === 0}>{pending ? "Guardando…" : "Guardar"}</button>
  </form></Modal>;
}

function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm"><span className="mb-1 block font-medium text-[var(--bf-ink)]">{label}</span>{children}</label>; }
