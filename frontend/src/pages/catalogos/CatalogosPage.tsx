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
import { ReferenciasAguaCatalog } from "./ReferenciasAguaCatalog";

const SECTIONS = [
  { id: "agua", label: "Agua" },
  { id: "biofloc", label: "Biofloc" },
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

  function setSeccion(id: SeccionId) {
    const next = new URLSearchParams(params);
    next.set("seccion", id);
    setParams(next);
  }

  const specs: Record<SeccionId, NamedCatalogSpec[]> = {
    agua: [
      {
        title: "Parámetros de agua",
        queryKey: ["parametros-agua", "catalog"],
        list: () => listParametrosAgua(false),
        create: (body) => createParametroAgua(body as Parameters<typeof createParametroAgua>[0]),
        update: (id, body) => updateParametroAgua(id, body as Parameters<typeof updateParametroAgua>[1]),
        fields: ["nombre", "unidad", "descripcion", "activo"],
        canWrite: puedeEscribir,
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
      },
      {
        title: "Unidades",
        queryKey: ["unidades", "catalog"],
        list: listUnidades,
        create: (body) => createUnidad(body as Parameters<typeof createUnidad>[0]),
        update: (id, body) => updateUnidad(id, body as Parameters<typeof updateUnidad>[1]),
        fields: ["nombre", "simbolo", "activo"],
        canWrite: puedeEscribir,
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
        note: "afecta_stock es +1 o −1 según el contrato del API. El stock lo calcula el servidor.",
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
      },
      {
        title: "Estados de equipo",
        queryKey: ["estados-equipo", "catalog"],
        list: () => listEstadosEquipo(false),
        create: (body) => createEstadoEquipo(body as Parameters<typeof createEstadoEquipo>[0]),
        update: (id, body) => updateEstadoEquipo(id, body as Parameters<typeof updateEstadoEquipo>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
      },
      {
        title: "Tipos de mantenimiento",
        queryKey: ["tipos-mantenimiento", "catalog"],
        list: () => listTiposMantenimiento(false),
        create: (body) => createTipoMantenimiento(body as Parameters<typeof createTipoMantenimiento>[0]),
        update: (id, body) => updateTipoMantenimiento(id, body as Parameters<typeof updateTipoMantenimiento>[1]),
        fields: ["nombre", "descripcion", "activo"],
        canWrite: puedeEscribir,
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
      },
      {
        title: "Niveles de alarma",
        queryKey: ["niveles-alarma", "catalog"],
        list: listNivelesAlarma,
        create: (body) => createNivelAlarma(body as Parameters<typeof createNivelAlarma>[0]),
        update: (id, body) => updateNivelAlarma(id, body as Parameters<typeof updateNivelAlarma>[1]),
        fields: ["nombre", "prioridad"],
        canWrite: puedeEscribir,
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
        description="Tipos y parámetros de apoyo a la operación. No hay eliminación: donde el API lo permite, se desactiva."
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

      {specs[seccion].map((spec) => (
        <NamedCatalogPanel key={spec.title} spec={spec} />
      ))}
      {seccion === "agua" ? <ReferenciasAguaCatalog canWrite={puedeEscribir} /> : null}
    </div>
  );
}
