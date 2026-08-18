import { useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { listEstadosAlarma, listTiposAlarma } from "../../api/alarms";
import { listEquipos } from "../../api/equipment";
import { listCategoriasGasto } from "../../api/finance";
import { listProductos } from "../../api/inventory";
import { listParametrosAgua } from "../../api/operations";
import { listLotes } from "../../api/production";
import { getReporte, type ReportParams } from "../../api/reports";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatDate, formatDateTime, formatNumber } from "../../utils/format";
import {
  CLASIFICACIONES_INVENTARIO,
  REPORTS,
  type ReportCommon,
  type ReportDef,
  type ReportId,
} from "../../types/reports";

type Row = Record<string, unknown>;

function isReportId(value: string | null): value is ReportId {
  return REPORTS.some((row) => row.id === value);
}

function cell(row: Row, key: string): ReactNode {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}

function cop(row: Row, key: string): string {
  return formatCop(row[key] as string | number | null);
}

function qty(row: Row, key: string): string {
  return formatNumber(row[key] as string | number | null, { maximumFractionDigits: 4 });
}

function dateCell(row: Row, key: string): string {
  return formatDate(row[key] as string | null);
}

function dt(row: Row, key: string): string {
  return formatDateTime(row[key] as string | null);
}

function columnsFor(id: ReportId): DataTableColumn<Row>[] {
  switch (id) {
    case "ventas":
      return [
        { key: "fecha", header: "Fecha", render: (row) => dateCell(row, "fecha") },
        { key: "cliente", header: "Cliente", render: (row) => cell(row, "cliente") },
        { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
        { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
        { key: "precio_unitario", header: "Precio unitario", render: (row) => cop(row, "precio_unitario") },
        { key: "subtotal", header: "Subtotal", render: (row) => cop(row, "subtotal") },
        { key: "venta_total", header: "Total venta", render: (row) => cop(row, "venta_total") },
        { key: "registrado_por_nombre", header: "Registró", render: (row) => cell(row, "registrado_por_nombre") },
      ];
    case "compras":
      return [
        { key: "fecha", header: "Fecha", render: (row) => dateCell(row, "fecha") },
        { key: "proveedor", header: "Proveedor", render: (row) => cell(row, "proveedor") },
        { key: "producto_codigo", header: "Producto", render: (row) => `${cell(row, "producto_codigo")} · ${cell(row, "producto_nombre")}` },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
        { key: "precio_unitario", header: "Precio unitario", render: (row) => cop(row, "precio_unitario") },
        { key: "subtotal", header: "Subtotal", render: (row) => cop(row, "subtotal") },
        { key: "compra_total", header: "Total compra", render: (row) => cop(row, "compra_total") },
      ];
    case "gastos":
      return [
        { key: "fecha", header: "Fecha", render: (row) => dateCell(row, "fecha") },
        { key: "categoria", header: "Categoría", render: (row) => cell(row, "categoria") },
        { key: "descripcion", header: "Descripción", render: (row) => cell(row, "descripcion") },
        { key: "proveedor", header: "Proveedor", render: (row) => cell(row, "proveedor") },
        { key: "valor", header: "Valor", render: (row) => cop(row, "valor") },
        { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
      ];
    case "inventario":
      return [
        { key: "codigo", header: "Código", render: (row) => cell(row, "codigo") },
        { key: "nombre", header: "Nombre", render: (row) => cell(row, "nombre") },
        { key: "categoria_nombre", header: "Categoría", render: (row) => cell(row, "categoria_nombre") },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "stock_actual", header: "Stock actual", render: (row) => qty(row, "stock_actual") },
        { key: "stock_minimo", header: "Stock mínimo", render: (row) => qty(row, "stock_minimo") },
        {
          key: "clasificacion",
          header: "Clasificación",
          render: (row) => {
            const value = String(row.clasificacion ?? "");
            const tone = value === "SIN_STOCK" ? "danger" : value === "STOCK_BAJO" ? "warn" : "ok";
            return <StatusBadge label={value || "—"} tone={tone} />;
          },
        },
        { key: "activo", header: "Activo", render: (row) => cell(row, "activo") },
      ];
    case "movimientos":
      return [
        { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
        { key: "producto_codigo", header: "Producto", render: (row) => `${cell(row, "producto_codigo")} · ${cell(row, "producto_nombre")}` },
        { key: "tipo", header: "Tipo", render: (row) => cell(row, "tipo") },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
        { key: "costo_unitario", header: "Costo unitario", render: (row) => cop(row, "costo_unitario") },
        { key: "costo_total", header: "Costo total", render: (row) => cop(row, "costo_total") },
        { key: "referencia_tipo", header: "Referencia", render: (row) => cell(row, "referencia_tipo") },
      ];
    case "compras-inventario":
      return [
        { key: "fecha", header: "Fecha", render: (row) => dateCell(row, "fecha") },
        { key: "compra_id", header: "Compra", render: (row) => `#${cell(row, "compra_id")}` },
        { key: "proveedor", header: "Proveedor", render: (row) => cell(row, "proveedor") },
        { key: "producto_codigo", header: "Producto", render: (row) => cell(row, "producto_codigo") },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
        { key: "subtotal", header: "Subtotal", render: (row) => cop(row, "subtotal") },
        { key: "movimiento_id", header: "Movimiento", render: (row) => (row.movimiento_id == null ? "—" : `#${cell(row, "movimiento_id")}`) },
        { key: "referencia_tipo", header: "Referencia", render: (row) => cell(row, "referencia_tipo") },
        { key: "tipo_movimiento", header: "Tipo movimiento", render: (row) => cell(row, "tipo_movimiento") },
      ];
    case "produccion":
      return [
        { key: "codigo", header: "Lote", render: (row) => cell(row, "codigo") },
        { key: "estado", header: "Estado", render: (row) => cell(row, "estado") },
        { key: "estanque_codigo", header: "Estanque", render: (row) => cell(row, "estanque_codigo") },
        { key: "especie", header: "Especie", render: (row) => cell(row, "especie") },
        { key: "etapa", header: "Etapa", render: (row) => cell(row, "etapa") },
        { key: "fecha_siembra", header: "Siembra", render: (row) => dateCell(row, "fecha_siembra") },
        { key: "cantidad_sembrada", header: "Sembrados", render: (row) => formatNumber(row.cantidad_sembrada as number) },
        { key: "mortalidad_acumulada", header: "Mortalidad", render: (row) => formatNumber(row.mortalidad_acumulada as number) },
        { key: "peces_cosechados", header: "Cosechados", render: (row) => formatNumber(row.peces_cosechados as number) },
        { key: "poblacion_estimada", header: "Población estimada", render: (row) => formatNumber(row.poblacion_estimada as number) },
        { key: "supervivencia_porcentaje", header: "Supervivencia %", render: (row) => qty(row, "supervivencia_porcentaje") },
        { key: "peso_promedio_g", header: "Peso promedio (g)", render: (row) => qty(row, "peso_promedio_g") },
      ];
    case "agua":
      return [
        { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
        { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
        { key: "parametro", header: "Parámetro", render: (row) => cell(row, "parametro") },
        { key: "valor", header: "Valor", render: (row) => qty(row, "valor") },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "valor_minimo", header: "Mín. ref.", render: (row) => qty(row, "valor_minimo") },
        { key: "valor_maximo", header: "Máx. ref.", render: (row) => qty(row, "valor_maximo") },
        {
          key: "fuera_de_rango",
          header: "Fuera de rango",
          render: (row) =>
            row.fuera_de_rango == null ? (
              "—"
            ) : (
              <StatusBadge label={row.fuera_de_rango ? "Sí" : "No"} tone={row.fuera_de_rango ? "warn" : "ok"} />
            ),
        },
      ];
    case "alimentacion":
      return [
        { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
        { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
        { key: "producto_codigo", header: "Producto", render: (row) => cell(row, "producto_codigo") },
        { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
        { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
        { key: "observaciones", header: "Observaciones", render: (row) => cell(row, "observaciones") },
        { key: "registrado_por_nombre", header: "Registró", render: (row) => cell(row, "registrado_por_nombre") },
      ];
    case "equipos":
      return [
        { key: "codigo", header: "Código", render: (row) => cell(row, "codigo") },
        { key: "nombre", header: "Nombre", render: (row) => cell(row, "nombre") },
        { key: "tipo", header: "Tipo", render: (row) => cell(row, "tipo") },
        { key: "estado", header: "Estado", render: (row) => cell(row, "estado") },
        { key: "ubicacion", header: "Ubicación", render: (row) => cell(row, "ubicacion") },
        { key: "activo", header: "Activo", render: (row) => cell(row, "activo") },
      ];
    case "mantenimientos":
      return [
        { key: "fecha", header: "Fecha", render: (row) => dateCell(row, "fecha") },
        { key: "equipo_codigo", header: "Equipo", render: (row) => cell(row, "equipo_codigo") },
        { key: "tipo", header: "Tipo", render: (row) => cell(row, "tipo") },
        { key: "descripcion", header: "Descripción", render: (row) => cell(row, "descripcion") },
        { key: "costo", header: "Costo", render: (row) => cop(row, "costo") },
        { key: "observaciones", header: "Observaciones", render: (row) => cell(row, "observaciones") },
      ];
    case "fallas":
      return [
        { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
        { key: "equipo_codigo", header: "Equipo", render: (row) => cell(row, "equipo_codigo") },
        { key: "descripcion", header: "Descripción", render: (row) => cell(row, "descripcion") },
        { key: "impacto", header: "Impacto", render: (row) => cell(row, "impacto") },
        { key: "solucion", header: "Solución", render: (row) => cell(row, "solucion") },
        { key: "costo", header: "Costo", render: (row) => cop(row, "costo") },
      ];
    case "energia":
      return [
        { key: "fecha_hora_inicio", header: "Inicio", render: (row) => dt(row, "fecha_hora_inicio") },
        { key: "fecha_hora_fin", header: "Fin", render: (row) => dt(row, "fecha_hora_fin") },
        { key: "tipo", header: "Tipo", render: (row) => cell(row, "tipo") },
        { key: "duracion_minutos", header: "Duración (min)", render: (row) => formatNumber(row.duracion_minutos as number | null) },
        { key: "respaldo_activado", header: "Respaldo", render: (row) => cell(row, "respaldo_activado") },
        { key: "observaciones", header: "Observaciones", render: (row) => cell(row, "observaciones") },
      ];
    case "alarmas":
      return [
        { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
        { key: "tipo", header: "Tipo", render: (row) => cell(row, "tipo") },
        { key: "nivel", header: "Nivel", render: (row) => cell(row, "nivel") },
        { key: "estado", header: "Estado", render: (row) => <StatusBadge label={String(row.estado ?? "—")} /> },
        { key: "titulo", header: "Título", render: (row) => cell(row, "titulo") },
        { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
        { key: "equipo_codigo", header: "Equipo", render: (row) => cell(row, "equipo_codigo") },
      ];
    default:
      return [];
  }
}

const BIOFLOC_MED: DataTableColumn<Row>[] = [
  { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
  { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
  { key: "volumen_sedimentable", header: "Vol. sedimentable", render: (row) => qty(row, "volumen_sedimentable") },
  { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
  { key: "relacion_cn", header: "Relación C:N", render: (row) => qty(row, "relacion_cn") },
];

const BIOFLOC_APL: DataTableColumn<Row>[] = [
  { key: "fecha_hora", header: "Fecha", render: (row) => dt(row, "fecha_hora") },
  { key: "lote_codigo", header: "Lote", render: (row) => cell(row, "lote_codigo") },
  { key: "tipo_aplicacion", header: "Tipo", render: (row) => cell(row, "tipo_aplicacion") },
  { key: "cantidad", header: "Cantidad", render: (row) => qty(row, "cantidad") },
  { key: "unidad", header: "Unidad", render: (row) => cell(row, "unidad") },
];

export function ReportesPage() {
  const [params, setParams] = useSearchParams();
  const tipoParam = params.get("tipo");
  const reportId: ReportId = isReportId(tipoParam) ? tipoParam : "produccion";
  const report = REPORTS.find((row) => row.id === reportId) ?? REPORTS[0];
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [loteId, setLoteId] = useState("");
  const [productoId, setProductoId] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [cliente, setCliente] = useState("");
  const [proveedor, setProveedor] = useState("");
  const [parametroId, setParametroId] = useState("");
  const [equipoId, setEquipoId] = useState("");
  const [tipoAlarmaId, setTipoAlarmaId] = useState("");
  const [estadoAlarmaId, setEstadoAlarmaId] = useState("");
  const [clasificacion, setClasificacion] = useState("");
  const [soloActivos, setSoloActivos] = useState(true);
  const [activo, setActivo] = useState("");
  const [tipo, setTipo] = useState("");
  const [referenciaTipo, setReferenciaTipo] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [request, setRequest] = useState<{ path: string; params: ReportParams } | null>(null);

  const needs = (key: ReportDef["filters"][number]) => report.filters.includes(key);
  const lotesQuery = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes(), enabled: needs("lote_id") });
  const productosQuery = useQuery({
    queryKey: ["productos", { soloActivos: false }],
    queryFn: () => listProductos({ soloActivos: false }),
    enabled: needs("producto_id"),
  });
  const categoriasQuery = useQuery({
    queryKey: ["categorias-gasto"],
    queryFn: () => listCategoriasGasto(false),
    enabled: needs("categoria_id"),
  });
  const parametrosQuery = useQuery({
    queryKey: ["parametros-agua"],
    queryFn: () => listParametrosAgua(false),
    enabled: needs("parametro_id"),
  });
  const equiposQuery = useQuery({
    queryKey: ["equipos", { soloActivos: false }],
    queryFn: () => listEquipos({ soloActivos: false }),
    enabled: needs("equipo_id"),
  });
  const tiposAlarmaQuery = useQuery({
    queryKey: ["tipos-alarma"],
    queryFn: () => listTiposAlarma(false),
    enabled: needs("tipo_alarma_id"),
  });
  const estadosAlarmaQuery = useQuery({
    queryKey: ["estados-alarma"],
    queryFn: listEstadosAlarma,
    enabled: needs("estado_alarma_id"),
  });

  const reporteQuery = useQuery({
    queryKey: ["reporte", request],
    queryFn: () => getReporte(request!.path, request!.params),
    enabled: Boolean(request),
  });

  function selectReport(id: ReportId) {
    const next = new URLSearchParams(params);
    next.set("tipo", id);
    setParams(next);
    setRequest(null);
    setFormError(null);
  }

  function buildParams(): ReportParams | null {
    if (fechaDesde && fechaHasta && fechaDesde > fechaHasta) {
      setFormError("fecha_desde debe ser <= fecha_hasta");
      return null;
    }
    const out: ReportParams = {};
    if (needs("fechas")) {
      if (fechaDesde) out.fecha_desde = fechaDesde;
      if (fechaHasta) out.fecha_hasta = fechaHasta;
    }
    if (needs("lote_id") && loteId) out.lote_id = Number(loteId);
    if (needs("producto_id") && productoId) out.producto_id = Number(productoId);
    if (needs("categoria_id") && categoriaId) out.categoria_id = Number(categoriaId);
    if (needs("cliente") && cliente.trim()) out.cliente = cliente.trim();
    if (needs("proveedor") && proveedor.trim()) out.proveedor = proveedor.trim();
    if (needs("parametro_id") && parametroId) out.parametro_id = Number(parametroId);
    if (needs("equipo_id") && equipoId) out.equipo_id = Number(equipoId);
    if (needs("tipo_alarma_id") && tipoAlarmaId) out.tipo_alarma_id = Number(tipoAlarmaId);
    if (needs("estado_alarma_id") && estadoAlarmaId) out.estado_alarma_id = Number(estadoAlarmaId);
    if (needs("clasificacion") && clasificacion) out.clasificacion = clasificacion;
    if (needs("solo_activos")) out.solo_activos = soloActivos;
    if (needs("activo") && activo === "true") out.activo = true;
    if (needs("activo") && activo === "false") out.activo = false;
    if (needs("tipo") && tipo.trim()) out.tipo = tipo.trim();
    if (needs("referencia_tipo") && referenciaTipo.trim()) out.referencia_tipo = referenciaTipo.trim();
    return out;
  }

  function generar() {
    setFormError(null);
    const built = buildParams();
    if (!built) return;
    setRequest({ path: report.path, params: built });
  }

  const data = reporteQuery.data;

  return (
    <div>
      <div className="no-print">
        <PageHeader
          title="Reportes"
          description="Consultas de solo lectura. Totales y columnas salen del API. Límite del servidor: 2000 filas."
          actions={
            data ? (
              <button type="button" className="bf-btn-secondary" onClick={() => window.print()}>
                Imprimir
              </button>
            ) : null
          }
        />

        <div className="mb-6 rounded-xl border border-[var(--bf-border)] bg-white p-4">
          <label className="mb-4 block max-w-md text-sm">
            <span className="mb-1 block text-[var(--bf-muted)]">Tipo de reporte</span>
            <select className="bf-input" value={report.id} onChange={(e) => selectReport(e.target.value as ReportId)}>
              {REPORTS.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.label}
                </option>
              ))}
            </select>
          </label>

          <div className="mb-4 flex flex-wrap items-end gap-3">
            {needs("fechas") ? (
              <>
                <Field label="Desde">
                  <input type="date" className="bf-input" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
                </Field>
                <Field label="Hasta">
                  <input type="date" className="bf-input" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
                </Field>
              </>
            ) : null}
            {needs("lote_id") ? (
              <Field label="Lote">
                <select className="bf-input" value={loteId} onChange={(e) => setLoteId(e.target.value)}>
                  <option value="">Todos</option>
                  {(lotesQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.codigo}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("producto_id") ? (
              <Field label="Producto">
                <select className="bf-input" value={productoId} onChange={(e) => setProductoId(e.target.value)}>
                  <option value="">Todos</option>
                  {(productosQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.codigo} · {row.nombre}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("categoria_id") ? (
              <Field label="Categoría">
                <select className="bf-input" value={categoriaId} onChange={(e) => setCategoriaId(e.target.value)}>
                  <option value="">Todas</option>
                  {(categoriasQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.nombre}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("cliente") ? (
              <Field label="Cliente">
                <input className="bf-input" value={cliente} onChange={(e) => setCliente(e.target.value)} />
              </Field>
            ) : null}
            {needs("proveedor") ? (
              <Field label="Proveedor">
                <input className="bf-input" value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
              </Field>
            ) : null}
            {needs("parametro_id") ? (
              <Field label="Parámetro">
                <select className="bf-input" value={parametroId} onChange={(e) => setParametroId(e.target.value)}>
                  <option value="">Todos</option>
                  {(parametrosQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.nombre}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("equipo_id") ? (
              <Field label="Equipo">
                <select className="bf-input" value={equipoId} onChange={(e) => setEquipoId(e.target.value)}>
                  <option value="">Todos</option>
                  {(equiposQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.codigo}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("tipo_alarma_id") ? (
              <Field label="Tipo de alarma">
                <select className="bf-input" value={tipoAlarmaId} onChange={(e) => setTipoAlarmaId(e.target.value)}>
                  <option value="">Todos</option>
                  {(tiposAlarmaQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.nombre}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("estado_alarma_id") ? (
              <Field label="Estado">
                <select className="bf-input" value={estadoAlarmaId} onChange={(e) => setEstadoAlarmaId(e.target.value)}>
                  <option value="">Todos</option>
                  {(estadosAlarmaQuery.data ?? []).map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.nombre}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("clasificacion") ? (
              <Field label="Clasificación">
                <select className="bf-input" value={clasificacion} onChange={(e) => setClasificacion(e.target.value)}>
                  <option value="">Todas</option>
                  {CLASIFICACIONES_INVENTARIO.map((row) => (
                    <option key={row} value={row}>
                      {row}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            {needs("solo_activos") ? (
              <label className="flex items-center gap-2 pb-2 text-sm">
                <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)} />
                Solo activos
              </label>
            ) : null}
            {needs("activo") ? (
              <Field label="Activo">
                <select className="bf-input" value={activo} onChange={(e) => setActivo(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="true">Activos</option>
                  <option value="false">Inactivos</option>
                </select>
              </Field>
            ) : null}
            {needs("tipo") ? (
              <Field label="Tipo">
                <input className="bf-input" value={tipo} onChange={(e) => setTipo(e.target.value)} placeholder="texto del API" />
              </Field>
            ) : null}
            {needs("referencia_tipo") ? (
              <Field label="Referencia tipo">
                <input className="bf-input" value={referenciaTipo} onChange={(e) => setReferenciaTipo(e.target.value)} />
              </Field>
            ) : null}
          </div>

          {report.note ? <p className="mb-3 text-xs text-[var(--bf-muted)]">{report.note}</p> : null}
          {formError ? <div className="mb-3"><ErrorAlert message={formError} /></div> : null}
          <button type="button" className="bf-btn-primary" onClick={generar}>
            Generar reporte
          </button>
        </div>
      </div>

      {reporteQuery.isFetching ? <LoadingState label="Generando reporte…" /> : null}
      {reporteQuery.isError ? <ErrorAlert message={apiErrorMessage(reporteQuery.error)} /> : null}
      {data ? <ReportResult report={report} data={data} /> : null}
    </div>
  );
}

function ReportResult({ report, data }: { report: ReportDef; data: ReportCommon }) {
  const kpis = useMemo(() => {
    const items: { label: string; value: ReactNode }[] = [
      { label: "Registros", value: formatNumber(data.total_registros) },
    ];
    if (data.n_ventas != null) items.push({ label: "N° ventas", value: formatNumber(data.n_ventas) });
    if (data.n_compras != null) items.push({ label: "N° compras", value: formatNumber(data.n_compras) });
    if (data.suma_subtotales != null) items.push({ label: "Suma subtotales", value: formatCop(data.suma_subtotales) });
    if (data.total_valor != null) items.push({ label: "Total valor", value: formatCop(data.total_valor) });
    if (data.suma_costo_total != null) items.push({ label: "Suma costo total", value: formatCop(data.suma_costo_total) });
    if (data.total_costo != null) items.push({ label: "Total costo", value: formatCop(data.total_costo) });
    return items;
  }, [data]);

  return (
    <div>
      <h2 className="mb-3 font-display text-lg font-semibold">{report.label}</h2>
      <p className="mb-4 text-xs text-[var(--bf-muted)]">
        Generado: {formatDateTime(data.generado_en)}
        {data.fecha_desde || data.fecha_hasta
          ? ` · Período: ${data.fecha_desde ?? "—"} — ${data.fecha_hasta ?? "—"}`
          : ""}
      </p>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((item) => (
          <KpiCard key={item.label} label={item.label} value={item.value} />
        ))}
      </div>
      {data.cantidad_por_unidad && data.cantidad_por_unidad.length > 0 ? (
        <p className="mb-4 text-sm text-[var(--bf-muted)]">
          Cantidad por unidad:{" "}
          {data.cantidad_por_unidad.map((row) => `${row.unidad} ${formatNumber(row.cantidad, { maximumFractionDigits: 3 })}`).join(" · ")}
        </p>
      ) : null}
      {data.nota ? <p className="mb-4 text-xs text-[var(--bf-muted)]">{data.nota}</p> : null}

      {report.id === "biofloc" ? (
        <div className="space-y-6">
          <section>
            <h3 className="mb-2 text-sm font-medium">Mediciones</h3>
            <DataTable
              rows={(data.mediciones ?? []) as Row[]}
              rowKey={(row) => Number(row.medicion_id)}
              empty="No hay mediciones."
              columns={BIOFLOC_MED}
            />
          </section>
          <section>
            <h3 className="mb-2 text-sm font-medium">Aplicaciones</h3>
            <DataTable
              rows={(data.aplicaciones ?? []) as Row[]}
              rowKey={(row) => Number(row.aplicacion_id)}
              empty="No hay aplicaciones."
              columns={BIOFLOC_APL}
            />
          </section>
        </div>
      ) : (
        <DataTable
          rows={(data.filas ?? []) as Row[]}
          rowKey={(row) =>
            String(
              row.detalle_id ??
                row.movimiento_id ??
                row.gasto_id ??
                row.medicion_id ??
                row.alimentacion_id ??
                row.mantenimiento_id ??
                row.falla_id ??
                row.evento_id ??
                row.alarma_id ??
                row.compra_id ??
                row.venta_id ??
                row.lote_id ??
                row.producto_id ??
                row.equipo_id ??
                row.codigo,
            )
          }
          empty="No hay registros."
          columns={columnsFor(report.id)}
        />
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="text-sm">
      <span className="mb-1 block text-[var(--bf-muted)]">{label}</span>
      {children}
    </label>
  );
}
