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
import {
  createProducto,
  listAlertasStockBajo,
  listCategoriasInventario,
  listProductos,
  listProductosStock,
  updateProducto,
} from "../../api/inventory";
import { listUnidades } from "../../api/operations";
import { apiErrorMessage } from "../../utils/apiError";
import { formatNumber, etiquetaProducto } from "../../utils/format";
import { can } from "../../utils/rbac";
import type { Producto, ProductoCreate, ProductoUpdate } from "../../types/inventory";

type ProductoForm = {
  codigo: string;
  nombre: string;
  categoria_id: number;
  unidad_id: number;
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

  const productosQuery = useQuery({
    queryKey: ["productos", { soloActivos: !incluirInactivos }],
    queryFn: () => listProductos({ soloActivos: !incluirInactivos }),
  });
  const stockQuery = useQuery({ queryKey: ["productos-stock"], queryFn: listProductosStock });
  const alertasQuery = useQuery({
    queryKey: ["alertas-stock-bajo", incluirInactivos],
    queryFn: () =>
      listAlertasStockBajo({
        soloActivos: !incluirInactivos,
        incluirNormal: true,
      }),
  });
  const stockBajoQuery = useQuery({
    queryKey: ["alertas-stock-bajo-seccion"],
    queryFn: () => listAlertasStockBajo({ soloActivos: true, incluirNormal: false }),
  });
  const categoriasQuery = useQuery({
    queryKey: ["categorias-inventario"],
    queryFn: () => listCategoriasInventario(false),
  });
  const unidadesQuery = useQuery({ queryKey: ["unidades"], queryFn: listUnidades });

  const categorias = useMemo(
    () => new Map((categoriasQuery.data ?? []).map((row) => [row.id, row])),
    [categoriasQuery.data],
  );
  const unidades = useMemo(() => new Map((unidadesQuery.data ?? []).map((row) => [row.id, row])), [unidadesQuery.data]);
  const stockMap = useMemo(
    () => new Map((stockQuery.data ?? []).map((row) => [row.producto_id, row])),
    [stockQuery.data],
  );
  const clasificacionMap = useMemo(
    () => new Map((alertasQuery.data ?? []).map((row) => [row.producto_id, row])),
    [alertasQuery.data],
  );
  const productosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const rows = productosQuery.data ?? [];
    if (!q) return rows;
    return rows.filter(
      (row) => row.nombre.toLowerCase().includes(q) || row.codigo.toLowerCase().includes(q),
    );
  }, [productosQuery.data, busqueda]);

  const form = useForm<ProductoForm>();

  const createMut = useMutation({
    mutationFn: (data: ProductoCreate) => createProducto(data),
    onSuccess: async () => {
      setCreating(false);
      setFormError(null);
      await invalidateInventario(queryClient);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductoUpdate }) => updateProducto(id, data),
    onSuccess: async () => {
      setEditing(null);
      setToToggle(null);
      setFormError(null);
      await invalidateInventario(queryClient);
    },
    onError: (error) => setFormError(apiErrorMessage(error)),
  });

  function openCreate() {
    setFormError(null);
    form.reset({
      codigo: "",
      nombre: "",
      categoria_id: categoriasQuery.data?.[0]?.id ?? 0,
      unidad_id: unidadesQuery.data?.[0]?.id ?? 0,
      stock_minimo: 0,
      activo: true,
    });
    setCreating(true);
  }

  function openEdit(producto: Producto) {
    setFormError(null);
    form.reset({
      codigo: producto.codigo,
      nombre: producto.nombre,
      categoria_id: producto.categoria_id,
      unidad_id: producto.unidad_id,
      stock_minimo: Number(producto.stock_minimo),
      activo: producto.activo,
    });
    setEditing(producto);
  }

  const loading = productosQuery.isLoading || stockQuery.isLoading || alertasQuery.isLoading;
  const error = productosQuery.error ?? stockQuery.error ?? alertasQuery.error;

  return (
    <div>
      <PageHeader
        title="Inventario"
        description="Productos y stock por unidad. No se suman kg con litros. Stock y clasificación salen del API, no se calculan aquí."
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
            {puedeEscribir ? (
              <button type="button" className="bf-btn-primary" onClick={openCreate}>
                Nuevo producto
              </button>
            ) : null}
          </div>
        }
      />

      <section className="mb-6 rounded-xl border border-[var(--bf-border)] bg-white p-4">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Stock bajo</h2>
            <p className="text-sm text-[var(--bf-muted)]">
              Alertas de inventario del API. No son las alarmas del sistema de la granja.
            </p>
          </div>
          <Link to="/inventario/movimientos" className="bf-btn-secondary">
            Ver movimientos
          </Link>
        </div>
        {stockBajoQuery.isLoading ? <LoadingState /> : null}
        {stockBajoQuery.isError ? <ErrorAlert message={apiErrorMessage(stockBajoQuery.error)} /> : null}
        {stockBajoQuery.data ? (
          <DataTable
            rows={stockBajoQuery.data}
            rowKey={(row) => row.producto_id}
            empty="No hay productos en SIN_STOCK ni STOCK_BAJO."
            columns={[
              { key: "codigo", header: "Producto", render: (row) => etiquetaProducto(row.nombre, row.codigo) },
              {
                key: "stock",
                header: "Stock",
                render: (row) => `${formatNumber(row.stock_actual, { maximumFractionDigits: 3 })} ${row.unidad}`,
              },
              {
                key: "min",
                header: "Stock mínimo",
                render: (row) => `${formatNumber(row.stock_minimo, { maximumFractionDigits: 3 })} ${row.unidad}`,
              },
              { key: "unidad", header: "Unidad", render: (row) => row.unidad },
              {
                key: "clasif",
                header: "Clasificación",
                render: (row) => (
                  <StatusBadge label={row.clasificacion} tone={toneClasificacion(row.clasificacion)} />
                ),
              },
            ]}
          />
        ) : null}
      </section>

      {loading ? <LoadingState label="Cargando productos…" /> : null}
      {error ? <ErrorAlert message={apiErrorMessage(error)} /> : null}

      {productosQuery.data ? (
        <div className="mb-3">
          <label className="text-sm">
            <span className="mb-1 block text-[var(--bf-muted)]">Buscar por nombre</span>
            <input
              className="bf-input max-w-md"
              value={busqueda}
              placeholder="Buscar producto…"
              onChange={(event) => setBusqueda(event.target.value)}
            />
          </label>
        </div>
      ) : null}

      {productosQuery.data ? (
        <DataTable
          rows={productosFiltrados}
          rowKey={(row) => row.id}
          empty="No hay productos."
          columns={[
            { key: "codigo", header: "Código", render: (row) => row.codigo },
            { key: "nombre", header: "Nombre", render: (row) => row.nombre },
            {
              key: "cat",
              header: "Categoría",
              render: (row) => categorias.get(row.categoria_id)?.nombre ?? `#${row.categoria_id}`,
            },
            {
              key: "unidad",
              header: "Unidad",
              render: (row) => {
                const unidad = unidades.get(row.unidad_id);
                const stockUnidad = stockMap.get(row.id)?.unidad;
                return stockUnidad ?? (unidad ? unidad.simbolo : `#${row.unidad_id}`);
              },
            },
            {
              key: "stock",
              header: "Stock",
              render: (row) => {
                const stock = stockMap.get(row.id);
                if (!stock) return "—";
                return formatNumber(stock.stock_actual, { maximumFractionDigits: 3 });
              },
            },
            {
              key: "min",
              header: "Stock mínimo",
              render: (row) => formatNumber(row.stock_minimo, { maximumFractionDigits: 3 }),
            },
            {
              key: "clasif",
              header: "Clasificación",
              render: (row) => {
                const alerta = clasificacionMap.get(row.id);
                if (!alerta) return "No hay clasificación disponible";
                return <StatusBadge label={alerta.clasificacion} tone={toneClasificacion(alerta.clasificacion)} />;
              },
            },
            {
              key: "activo",
              header: "Activo",
              render: (row) => <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} />,
            },
            {
              key: "acciones",
              header: "",
              render: (row) =>
                puedeEscribir ? (
                  <div className="flex justify-end gap-2">
                    <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => openEdit(row)}>
                      Editar
                    </button>
                    <button type="button" className="bf-btn-secondary !py-1 text-xs" onClick={() => setToToggle(row)}>
                      {row.activo ? "Desactivar" : "Activar"}
                    </button>
                  </div>
                ) : null,
            },
          ]}
        />
      ) : null}

      <ProductoModal
        open={creating || Boolean(editing)}
        title={editing ? "Editar producto" : "Nuevo producto"}
        form={form}
        formError={formError}
        categorias={categoriasQuery.data ?? []}
        unidades={unidadesQuery.data ?? []}
        pending={createMut.isPending || updateMut.isPending}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSubmit={(values) => {
          const payload = {
            codigo: values.codigo.trim(),
            nombre: values.nombre.trim(),
            categoria_id: Number(values.categoria_id),
            unidad_id: Number(values.unidad_id),
            stock_minimo: Number(values.stock_minimo),
            activo: values.activo,
          };
          if (editing) {
            updateMut.mutate({ id: editing.id, data: payload });
          } else {
            createMut.mutate(payload);
          }
        }}
      />

      <ConfirmDialog
        open={Boolean(toToggle)}
        title={toToggle?.activo ? "Desactivar producto" : "Activar producto"}
        description="El API no permite eliminar productos. Se cambia el campo activo."
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

function invalidateInventario(queryClient: ReturnType<typeof useQueryClient>) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["productos"] }),
    queryClient.invalidateQueries({ queryKey: ["productos-stock"] }),
    queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo"] }),
    queryClient.invalidateQueries({ queryKey: ["alertas-stock-bajo-seccion"] }),
    queryClient.invalidateQueries({ queryKey: ["productos-activos"] }),
  ]);
}

function ProductoModal({
  open,
  title,
  form,
  formError,
  categorias,
  unidades,
  pending,
  onClose,
  onSubmit,
}: {
  open: boolean;
  title: string;
  form: ReturnType<typeof useForm<ProductoForm>>;
  formError: string | null;
  categorias: { id: number; nombre: string }[];
  unidades: { id: number; nombre: string; simbolo: string }[];
  pending: boolean;
  onClose: () => void;
  onSubmit: (values: ProductoForm) => void;
}) {
  return (
    <Modal open={open} title={title} onClose={onClose}>
      <form className="space-y-3" onSubmit={form.handleSubmit(onSubmit)}>
        {formError ? <ErrorAlert message={formError} /> : null}
        {categorias.length === 0 ? (
          <ErrorAlert message="El formulario de alta requiere categorías que la API no devolvió." />
        ) : null}
        <Field label="Código">
          <input className="bf-input" {...form.register("codigo", { required: true })} />
        </Field>
        <Field label="Nombre">
          <input className="bf-input" {...form.register("nombre", { required: true })} />
        </Field>
        <Field label="Categoría">
          <select className="bf-input" {...form.register("categoria_id", { valueAsNumber: true })}>
            {categorias.map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Unidad">
          <select className="bf-input" {...form.register("unidad_id", { valueAsNumber: true })}>
            {unidades.map((row) => (
              <option key={row.id} value={row.id}>
                {row.nombre} ({row.simbolo})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Stock mínimo">
          <input
            type="number"
            step="any"
            min="0"
            className="bf-input"
            {...form.register("stock_minimo", { valueAsNumber: true })}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...form.register("activo")} />
          Activo
        </label>
        <button type="submit" className="bf-btn-primary" disabled={pending || categorias.length === 0 || unidades.length === 0}>
          {pending ? "Guardando…" : "Guardar"}
        </button>
      </form>
    </Modal>
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
