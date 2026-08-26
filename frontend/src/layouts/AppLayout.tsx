import { useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bell, LogOut, Menu, User, X } from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { listAlarmas, listEstadosAlarma } from "../api/alarms";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { can } from "../utils/rbac";

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  adminOnly?: boolean;
  catalogOnly?: boolean;
};

type NavSection = {
  id: string;
  label: string;
  items: NavItem[];
};

const NAV: NavSection[] = [
  {
    id: "general",
    label: "General",
    items: [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/alarmas", label: "Alarmas" },
    ],
  },
  {
    id: "produccion",
    label: "Producción",
    items: [
      { to: "/produccion/estanques", label: "Estanques" },
      { to: "/produccion/lotes", label: "Lotes" },
      { to: "/produccion/biometrias", label: "Biometrías" },
      { to: "/produccion/mortalidades", label: "Mortalidades" },
      { to: "/produccion/cosechas", label: "Cosechas" },
    ],
  },
  {
    id: "inventario",
    label: "Inventario",
    items: [
      { to: "/inventario", label: "Productos", end: true },
      { to: "/inventario/movimientos", label: "Movimientos" },
      { to: "/compras", label: "Compras" },
    ],
  },
  {
    id: "finanzas",
    label: "Finanzas",
    items: [
      { to: "/finanzas/ventas", label: "Ventas" },
      { to: "/finanzas/gastos", label: "Gastos" },
    ],
  },
  {
    id: "equipos",
    label: "Equipos",
    items: [
      { to: "/equipos", label: "Equipos", end: true },
      { to: "/equipos/mantenimientos", label: "Mantenimientos" },
      { to: "/equipos/mantenimientos?tab=fallas", label: "Fallas" },
      { to: "/energia", label: "Energía" },
    ],
  },
  {
    id: "reportes",
    label: "Análisis / Reportes",
    items: [{ to: "/reportes", label: "Reportes" }],
  },
  {
    id: "admin",
    label: "Administración",
    items: [
      { to: "/catalogos", label: "Catálogos", catalogOnly: true },
      { to: "/admin/usuarios", label: "Usuarios", adminOnly: true },
    ],
  },
];

type Crumb = { label: string; to?: string };

const CRUMBS: { prefix: string; title: string; trail: Crumb[] }[] = [
  { prefix: "/dashboard", title: "Dashboard", trail: [{ label: "General" }, { label: "Dashboard" }] },
  { prefix: "/perfil", title: "Perfil", trail: [{ label: "Cuenta" }, { label: "Perfil" }] },
  { prefix: "/produccion/estanques/", title: "Ficha del estanque", trail: [{ label: "Producción", to: "/produccion/estanques" }, { label: "Estanques", to: "/produccion/estanques" }, { label: "Ficha" }] },
  { prefix: "/produccion/estanques", title: "Estanques", trail: [{ label: "Producción" }, { label: "Estanques" }] },
  { prefix: "/produccion/lotes/", title: "Ficha del lote", trail: [{ label: "Producción", to: "/produccion/lotes" }, { label: "Lotes", to: "/produccion/lotes" }, { label: "Ficha" }] },
  { prefix: "/produccion/lotes", title: "Lotes", trail: [{ label: "Producción" }, { label: "Lotes" }] },
  { prefix: "/produccion/biometrias", title: "Biometrías", trail: [{ label: "Producción" }, { label: "Biometrías" }] },
  { prefix: "/produccion/mortalidades", title: "Mortalidades", trail: [{ label: "Producción" }, { label: "Mortalidades" }] },
  { prefix: "/produccion/cosechas", title: "Cosechas", trail: [{ label: "Producción" }, { label: "Cosechas" }] },
  { prefix: "/operacion/agua", title: "Agua", trail: [{ label: "Operación" }, { label: "Agua" }] },
  { prefix: "/operacion/biofloc", title: "Biofloc", trail: [{ label: "Operación" }, { label: "Biofloc" }] },
  { prefix: "/operacion/alimentacion", title: "Alimentación", trail: [{ label: "Operación" }, { label: "Alimentación" }] },
  { prefix: "/inventario/movimientos", title: "Movimientos", trail: [{ label: "Inventario" }, { label: "Movimientos" }] },
  { prefix: "/inventario", title: "Productos", trail: [{ label: "Inventario" }, { label: "Productos" }] },
  { prefix: "/compras/", title: "Detalle de compra", trail: [{ label: "Inventario", to: "/compras" }, { label: "Compras", to: "/compras" }, { label: "Detalle" }] },
  { prefix: "/compras", title: "Compras", trail: [{ label: "Inventario" }, { label: "Compras" }] },
  { prefix: "/finanzas/ventas/", title: "Detalle de venta", trail: [{ label: "Finanzas", to: "/finanzas/ventas" }, { label: "Ventas", to: "/finanzas/ventas" }, { label: "Detalle" }] },
  { prefix: "/finanzas/ventas", title: "Ventas", trail: [{ label: "Finanzas" }, { label: "Ventas" }] },
  { prefix: "/finanzas/gastos", title: "Gastos", trail: [{ label: "Finanzas" }, { label: "Gastos" }] },
  { prefix: "/finanzas", title: "Finanzas", trail: [{ label: "Finanzas" }] },
  { prefix: "/equipos/mantenimientos", title: "Mantenimientos", trail: [{ label: "Equipos" }, { label: "Mantenimientos" }] },
  { prefix: "/equipos", title: "Equipos", trail: [{ label: "Equipos" }] },
  { prefix: "/energia", title: "Energía", trail: [{ label: "Equipos" }, { label: "Energía" }] },
  { prefix: "/alarmas/", title: "Alarma", trail: [{ label: "General", to: "/alarmas" }, { label: "Alarmas", to: "/alarmas" }, { label: "Detalle" }] },
  { prefix: "/alarmas", title: "Alarmas", trail: [{ label: "General" }, { label: "Alarmas" }] },
  { prefix: "/reportes", title: "Reportes", trail: [{ label: "Análisis" }, { label: "Reportes" }] },
  { prefix: "/catalogos", title: "Catálogos", trail: [{ label: "Administración" }, { label: "Catálogos" }] },
  { prefix: "/admin/usuarios", title: "Usuarios", trail: [{ label: "Administración" }, { label: "Usuarios" }] },
];

function moduleFromPath(pathname: string, search: string): { title: string; trail: Crumb[] } {
  if (pathname.startsWith("/equipos/mantenimientos") && search.includes("tab=fallas")) {
    return { title: "Fallas", trail: [{ label: "Equipos" }, { label: "Fallas" }] };
  }
  const match = CRUMBS.find((row) => pathname.startsWith(row.prefix));
  return match ?? { title: "Biofloc ERP", trail: [{ label: "Inicio" }] };
}

function linkClass(active: boolean): string {
  return [
    "flex items-center rounded-xl px-3 py-2 text-sm transition-all duration-150",
    active
      ? "bg-white/12 font-semibold text-white shadow-[inset_3px_0_0_#5eead4]"
      : "text-white/68 hover:bg-white/8 hover:text-white",
  ].join(" ");
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [confirmSalir, setConfirmSalir] = useState(false);
  const modulo = moduleFromPath(location.pathname, location.search);

  const visibleNav = useMemo(
    () =>
      NAV.map((section) => ({
        ...section,
        items: section.items.filter((item) => {
          if (item.adminOnly && !can(user?.rol, "gestionarUsuarios")) return false;
          if (item.catalogOnly && !can(user?.rol, "verCatalogos")) return false;
          return true;
        }),
      })).filter((section) => section.items.length > 0),
    [user?.rol],
  );

  const estadosQuery = useQuery({
    queryKey: ["estados-alarma"],
    queryFn: listEstadosAlarma,
  });
  const pendienteId = estadosQuery.data?.find((row) => row.nombre === "PENDIENTE")?.id;
  const pendientesQuery = useQuery({
    queryKey: ["alarmas", { estadoAlarmaId: pendienteId }],
    queryFn: () => listAlarmas({ estadoAlarmaId: pendienteId }),
    enabled: Boolean(pendienteId),
  });
  const pendientes = pendientesQuery.data?.length ?? 0;

  return (
    <div className="min-h-screen bg-[var(--bf-bg)]">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-[var(--bf-border)] bg-[color-mix(in_srgb,var(--bf-header)_86%,transparent)] px-3 backdrop-blur-md sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            className="rounded-full p-2 text-[var(--bf-ink)] lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0 leading-tight">
            <p className="truncate font-display text-sm font-semibold tracking-wide text-[var(--bf-ink)]">
              {modulo.title}
            </p>
            <nav className="hidden truncate text-[11px] text-[var(--bf-muted)] sm:block">
              {modulo.trail.map((crumb, index) => (
                <span key={`${crumb.label}-${index}`}>
                  {index > 0 ? " / " : null}
                  {crumb.to ? (
                    <Link to={crumb.to} className="hover:text-[var(--bf-ink)] hover:underline">
                      {crumb.label}
                    </Link>
                  ) : (
                    crumb.label
                  )}
                </span>
              ))}
            </nav>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <button
            type="button"
            className="relative rounded-full p-2 text-[var(--bf-muted)] transition-colors hover:bg-[var(--bf-chip)] hover:text-[var(--bf-ink)]"
            onClick={() => navigate("/alarmas?estado=PENDIENTE")}
            aria-label={pendientes > 0 ? `Alarmas pendientes: ${pendientes}` : "Alarmas"}
            title="Notificaciones"
          >
            <Bell className="h-5 w-5" />
            {pendientes > 0 ? (
              <span className="absolute right-0.5 top-0.5 min-w-4 rounded-full bg-amber-600 px-1 text-center text-[10px] font-semibold leading-4 text-white shadow-sm">
                {pendientes}
              </span>
            ) : null}
          </button>
          <div className="hidden items-center gap-2 sm:flex">
            <span className="max-w-[160px] truncate text-sm text-[var(--bf-ink)]">{user?.nombre}</span>
            <StatusBadge label={user?.rol ?? "—"} tone="info" />
          </div>
          <button
            type="button"
            className="rounded-full p-2 text-[var(--bf-muted)] transition-colors hover:bg-[var(--bf-chip)] hover:text-[var(--bf-ink)]"
            onClick={() => navigate("/perfil")}
            aria-label="Perfil"
            title="Perfil"
          >
            <User className="h-5 w-5" />
          </button>
          <button type="button" className="bf-btn-secondary !px-3 !py-1.5 text-xs" onClick={() => setConfirmSalir(true)}>
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Salir</span>
          </button>
        </div>
      </header>

      <div className="flex">
        {sidebarOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-[var(--bf-ink)]/45 backdrop-blur-[2px] lg:hidden"
            aria-label="Cerrar menú"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}

        <aside
          className={[
            "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[var(--bf-sidebar)] lg:static lg:z-0 lg:min-h-[calc(100vh-3.5rem)]",
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            "transition-transform duration-200",
          ].join(" ")}
        >
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-5">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-2xl bg-teal-300/20 text-sm font-bold text-teal-100">
                B
              </span>
              <div>
                <p className="font-display text-sm font-semibold tracking-wide text-white">Biofloc ERP</p>
                <p className="text-[11px] text-white/50">Producción piscícola</p>
              </div>
            </div>
            <button type="button" className="p-1 text-white lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Cerrar">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
            {visibleNav.map((section) => (
              <div key={section.id}>
                <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
                  {section.label}
                </p>
                <div className="space-y-0.5">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      onClick={() => setSidebarOpen(false)}
                      className={({ isActive }) => {
                        const esFallas = item.to.includes("tab=fallas");
                        const enFallas =
                          location.pathname.startsWith("/equipos/mantenimientos") &&
                          location.search.includes("tab=fallas");
                        const active = esFallas
                          ? enFallas
                          : item.to === "/equipos/mantenimientos"
                            ? isActive && !enFallas
                            : isActive;
                        return linkClass(active);
                      }}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>
          <p className="px-4 pb-4 text-[11px] text-white/35">Control de granja · V1</p>
        </aside>

        <main className="min-h-[calc(100vh-3.5rem)] min-w-0 flex-1 px-4 py-6 sm:px-8 lg:px-10">
          <Outlet />
        </main>
      </div>

      <ConfirmDialog
        open={confirmSalir}
        title="Cerrar sesión"
        description="Se cerrará la sesión en este navegador."
        confirmLabel="Salir"
        onCancel={() => setConfirmSalir(false)}
        onConfirm={() => {
          setConfirmSalir(false);
          logout();
        }}
      />
    </div>
  );
}
