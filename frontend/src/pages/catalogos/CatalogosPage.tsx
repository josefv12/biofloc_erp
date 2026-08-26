import { useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../../auth/AuthProvider";
import {
  createCategoriaGasto,
  createCategoriaInventario,
  createEstadoAlarma,
  createEstadoEquipo,
  createNivelAlarma,
  createParametroAgua,
  createTipoAlarma,
  createTipoAplicacionBiofloc,
  createTipoEquipo,
  createTipoMantenimiento,
  createTipoMovimientoInventario,
  createUnidad,
  updateCategoriaGasto,
  updateCategoriaInventario,
  updateEstadoAlarma,
  updateEstadoEquipo,
  updateNivelAlarma,
  updateParametroAgua,
  updateTipoAlarma,
  updateTipoAplicacionBiofloc,
  updateTipoEquipo,
  updateTipoMantenimiento,
  updateTipoMovimientoInventario,
  updateUnidad,
} from "../../api/catalogs";
import { listEstadosAlarma, listNivelesAlarma, listTiposAlarma } from "../../api/alarms";
import { listEstadosEquipo, listTiposEquipo, listTiposMantenimiento } from "../../api/equipment";
import { listCategoriasGasto } from "../../api/finance";
import { listCategoriasInventario, listTiposMovimientoInventario } from "../../api/inventory";
import { listParametrosAgua, listTiposAplicacionBiofloc, listUnidades } from "../../api/operations";
import { can } from "../../utils/rbac";
import { NamedCatalogPanel, type NamedCatalogSpec } from "./NamedCatalogPanel";
import { EspeciesCatalog } from "./EspeciesCatalog";
import { EtapasProductivasCatalog } from "./EtapasProductivasCatalog";
import { ReferenciasAguaCatalog } from "./ReferenciasAguaCatalog";
import { ReferenciasBioflocCatalog } from "./ReferenciasBioflocCatalog";
import { ReferenciasProduccionCatalog } from "./ReferenciasProduccionCatalog";

const SECTIONS = [
  { id: "agua", label: "Agua" },
  { id: "biofloc", label: "Biofloc" },
  { id: "produccion", label: "Producción" },
  { id: "inventario", label: "Inventario" },
  { id: "finanzas", label: "Finanzas" },
  { id: "equipos", label: "Equipos" },
  { id: "alarmas", label: "Alarmas" },
] as const;

type SeccionId = (typeof SECTIONS)[number]["id"];

const ESTADOS_ALARMA_SEMILLA = new Set(["PENDIENTE", "ATENDIDA", "CERRADA"]);

function isSeccion(value: string | null): value is SeccionId {
  return SECTIONS.some((row) => row.id === value);
}

export function CatalogosPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const rawSeccion = params.get("seccion");
  const seccion: SeccionId = isSeccion(rawSeccion) ? rawSeccion : "agua";
  const puedeEscribir = can(user?.rol, "escribirCatalogo");
  const puedeEscribirMaestro = can(user?.rol, "escribirCatalogoMaestro");

  function setSeccion(id: SeccionId) {
    const next = new URLSearchParams(params);
    next.set("seccion", id);
    setParams(next);
  }

  const specs: Record<SeccionId, NamedCatalogSpec[]> = {
    produccion: [],
    agua: [
      {
        title: "Parámetros de agua",
        queryKey: ["parametros-agua", "catalog"],
        list: () => listParametrosAgua(false),
        create: (body) => createParametroAgua(body as Parameters<typeof createParametroAgua>[0]),
        update: (id, body) => updateParametroAgua(id, body as Parameters<typeof updateParametroAgua>[1]),
        fields: ["nombre", "unidad", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo parámetro",
        note: "La unidad es texto del propio parámetro (mg/L, °C, pH). No se toma del catálogo de inventario.",
      },
    ],
    biofloc: [
      {
        title: "Tipos de aplicación Biofloc",
        queryKey: ["tipos-aplicacion-biofloc", "catalog"],
        list: () => listTiposAplicacionBiofloc(false),
        create: (body) => createTipoAplicacionBiofloc(body as Parameters<typeof createTipoAplicacionBiofloc>[0]),
        update: (id, body) => updateTipoAplicacionBiofloc(id, body as Parameters<typeof updateTipoAplicacionBiofloc>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo tipo de aplicación",
        note: "Catálogo operativo de aplicaciones (carbono, probiótico, etc.). No es una referencia de medición.",
      },
    ],
    inventario: [
      {
        title: "Categorías de inventario",
        queryKey: ["categorias-inventario", "catalog"],
        list: () => listCategoriasInventario(false),
        create: (body) => createCategoriaInventario(body as Parameters<typeof createCategoriaInventario>[0]),
        update: (id, body) => updateCategoriaInventario(id, body as Parameters<typeof updateCategoriaInventario>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nueva categoría",
      },
      {
        title: "Unidades",
        queryKey: ["unidades", "catalog"],
        list: listUnidades,
        create: (body) => createUnidad(body as Parameters<typeof createUnidad>[0]),
        update: (id, body) => updateUnidad(id, body as Parameters<typeof updateUnidad>[1]),
        fields: ["nombre", "simbolo", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nueva unidad",
        note: "La lista sale del API. No hay DELETE: desactive con Inactivo si ya no debe usarse.",
      },
      {
        title: "Tipos de movimiento",
        queryKey: ["tipos-movimiento-inventario", "catalog"],
        list: listTiposMovimientoInventario,
        create: (body) => createTipoMovimientoInventario(body as Parameters<typeof createTipoMovimientoInventario>[0]),
        update: (id, body) =>
          updateTipoMovimientoInventario(id, body as Parameters<typeof updateTipoMovimientoInventario>[1]),
        fields: ["nombre", "descripcion", "afecta_stock"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo tipo de movimiento",
        note: "Efecto sobre el stock: +1 o −1 según el contrato del API. El stock lo calcula el servidor.",
      },
    ],
    finanzas: [
      {
        title: "Categorías de gasto",
        queryKey: ["categorias-gasto", "catalog"],
        list: () => listCategoriasGasto(false),
        create: (body) => createCategoriaGasto(body as Parameters<typeof createCategoriaGasto>[0]),
        update: (id, body) => updateCategoriaGasto(id, body as Parameters<typeof updateCategoriaGasto>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nueva categoría",
      },
    ],
    equipos: [
      {
        title: "Tipos de equipo",
        queryKey: ["tipos-equipo", "catalog"],
        list: () => listTiposEquipo(false),
        create: (body) => createTipoEquipo(body as Parameters<typeof createTipoEquipo>[0]),
        update: (id, body) => updateTipoEquipo(id, body as Parameters<typeof updateTipoEquipo>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo tipo de equipo",
      },
      {
        title: "Estados de equipo",
        queryKey: ["estados-equipo", "catalog"],
        list: () => listEstadosEquipo(false),
        create: (body) => createEstadoEquipo(body as Parameters<typeof createEstadoEquipo>[0]),
        update: (id, body) => updateEstadoEquipo(id, body as Parameters<typeof updateEstadoEquipo>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo estado",
      },
      {
        title: "Tipos de mantenimiento",
        queryKey: ["tipos-mantenimiento", "catalog"],
        list: () => listTiposMantenimiento(false),
        create: (body) => createTipoMantenimiento(body as Parameters<typeof createTipoMantenimiento>[0]),
        update: (id, body) => updateTipoMantenimiento(id, body as Parameters<typeof updateTipoMantenimiento>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo tipo de mantenimiento",
      },
    ],
    alarmas: [
      {
        title: "Tipos de alarma",
        queryKey: ["tipos-alarma", "catalog"],
        list: () => listTiposAlarma(false),
        create: (body) => createTipoAlarma(body as Parameters<typeof createTipoAlarma>[0]),
        update: (id, body) => updateTipoAlarma(id, body as Parameters<typeof updateTipoAlarma>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo tipo de alarma",
      },
      {
        title: "Niveles de alarma",
        queryKey: ["niveles-alarma", "catalog"],
        list: listNivelesAlarma,
        create: (body) => createNivelAlarma(body as Parameters<typeof createNivelAlarma>[0]),
        update: (id, body) => updateNivelAlarma(id, body as Parameters<typeof updateNivelAlarma>[1]),
        fields: ["nombre", "prioridad"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo nivel",
        note: "No tienen campo activo. La prioridad debe ser mayor que 0.",
      },
      {
        title: "Estados de alarma",
        queryKey: ["estados-alarma", "catalog"],
        list: listEstadosAlarma,
        create: (body) => createEstadoAlarma(body as Parameters<typeof createEstadoAlarma>[0]),
        update: (id, body) => updateEstadoAlarma(id, body as Parameters<typeof updateEstadoAlarma>[1]),
        fields: ["nombre", "descripcion"],
        canWrite: puedeEscribir,
        createLabel: "Nuevo estado",
        lockNombre: (nombre) => ESTADOS_ALARMA_SEMILLA.has(nombre),
        lockNombreHint: "PENDIENTE, ATENDIDA y CERRADA no se pueden renombrar. El servidor rechaza ese cambio.",
        note: "No tienen campo activo. Los estados semilla PENDIENTE, ATENDIDA y CERRADA no se pueden renombrar.",
      },
    ],
  };

  return (
    <div>
      <PageHeader
        title="Catálogos"
        description="Agua, Biofloc, producción, inventario, finanzas, equipos y alarmas. Los catálogos maestros (especies y referencias) los escribe solo el administrador. Referencia configurada por administrador: no es una recomendación universal."
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {SECTIONS.map((row) => (
          <button
            key={row.id}
            type="button"
            className={seccion === row.id ? "bf-btn-primary" : "bf-btn-secondary"}
            onClick={() => setSeccion(row.id)}
          >
            {row.label}
          </button>
        ))}
      </div>

      {seccion === "produccion" ? (
        <>
          <EspeciesCatalog canWrite={puedeEscribirMaestro} />
          <EtapasProductivasCatalog />
          <ReferenciasProduccionCatalog canWrite={puedeEscribirMaestro} />
        </>
      ) : null}
      {specs[seccion].map((spec) => (
        <NamedCatalogPanel key={spec.title} spec={spec} />
      ))}
      {seccion === "agua" ? <ReferenciasAguaCatalog canWrite={puedeEscribirMaestro} /> : null}
      {seccion === "biofloc" ? <ReferenciasBioflocCatalog canWrite={puedeEscribirMaestro} /> : null}
    </div>
  );
}
