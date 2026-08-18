import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  ChevronDown,
  Droplets,
  FileBarChart,
  LayoutDashboard,
  Library,
  LogOut,
  Menu,
  Package,
  User,
  Wallet,
  Waves,
  Wrench,
  X,
} from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { listAlarmas, listEstadosAlarma } from "../api/alarms";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { can } from "../utils/rbac";

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
};

type NavGroup = {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  items?: NavItem[];
  to?: string;
  catalogOnly?: boolean;
};

const NAV: NavGroup[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  {
    id: "produccion",
    label: "Producción",
    icon: Waves,
    items: [
      { to: "/produccion/estanques", label: "Estanques" },
      { to: "/produccion/lotes", label: "Lotes" },
    ],
  },
  {
    id: "operacion",
    label: "Operación",
    icon: Droplets,
    items: [
      { to: "/operacion/agua", label: "Agua" },
      { to: "/operacion/biofloc", label: "Biofloc" },
      { to: "/operacion/alimentacion", label: "Alimentación" },
    ],
  },
  {
    id: "inventario",
    label: "Inventario",
    icon: Package,
    items: [
      { to: "/inventario", label: "Stock y productos", end: true },
      { to: "/inventario/movimientos", label: "Movimientos" },
      { to: "/compras", label: "Compras" },
    ],
  },
  {
    id: "finanzas",
    label: "Finanzas",
    icon: Wallet,
    items: [
      { to: "/finanzas/gastos", label: "Gastos" },
      { to: "/finanzas/ventas", label: "Ventas" },
    ],
  },
  {
    id: "equipos",
    label: "Equipos",
    icon: Wrench,
    items: [
      { to: "/equipos", label: "Equipos", end: true },
      { to: "/equipos/mantenimientos", label: "Mantenimiento y fallas" },
      { to: "/energia", label: "Energía" },
    ],
  },
  { id: "alarmas", label: "Alarmas", icon: Bell, to: "/alarmas" },
  { id: "reportes", label: "Reportes", icon: FileBarChart, to: "/reportes" },
  { id: "catalogos", label: "Catálogos", icon: Library, to: "/catalogos", catalogOnly: true },
];

function linkClass(active: boolean): string {
  return [
    "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
    active
      ? "bg-white/12 font-medium text-white"
      : "text-white/75 hover:bg-white/8 hover:text-white",
  ].join(" ");
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [confirmSalir, setConfirmSalir] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    produccion: true,
    operacion: true,
    inventario: true,
    finanzas: true,
    equipos: true,
  });

  const visibleNav = NAV.filter((group) => !group.catalogOnly || can(user?.rol, "verCatalogos"));

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

  function toggleGroup(id: string) {
    setOpenGroups((current) => ({ ...current, [id]: !current[id] }));
  }

  return (
    <div className="min-h-screen bg-[var(--bf-bg)]">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-[var(--bf-border)] bg-[var(--bf-header)] px-3 sm:px-5">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-md p-2 text-[var(--bf-ink)] lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="leading-tight">
            <p className="font-display text-sm font-semibold tracking-wide text-[var(--bf-ink)]">
              Biofloc ERP
            </p>
            <p className="text-[11px] text-[var(--bf-muted)]">Piscicultura · V1</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            className="relative rounded-md p-2 text-[var(--bf-muted)] hover:bg-[var(--bf-chip)] hover:text-[var(--bf-ink)]"
            onClick={() => navigate("/alarmas?estado=PENDIENTE")}
            aria-label={pendientes > 0 ? `Alarmas pendientes: ${pendientes}` : "Alarmas"}
            title="Alarmas pendientes"
          >
            <Bell className="h-5 w-5" />
            {pendientes > 0 ? (
              <span className="absolute right-0.5 top-0.5 min-w-4 rounded-full bg-amber-700 px-1 text-center text-[10px] font-semibold leading-4 text-white">
                {pendientes}
              </span>
            ) : null}
          </button>
          <div className="hidden items-center gap-2 sm:flex">
            <span className="max-w-[180px] truncate text-sm text-[var(--bf-ink)]">{user?.nombre}</span>
            <StatusBadge label={user?.rol ?? "—"} tone="info" />
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-[var(--bf-muted)] hover:bg-[var(--bf-chip)] hover:text-[var(--bf-ink)]"
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
            className="fixed inset-0 z-30 bg-[var(--bf-ink)]/40 lg:hidden"
            aria-label="Cerrar menú"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}

        <aside
          className={[
            "fixed inset-y-0 left-0 z-40 flex w-60 flex-col bg-[var(--bf-sidebar)] pt-14 lg:static lg:z-0 lg:min-h-[calc(100vh-3.5rem)] lg:pt-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            "transition-transform",
          ].join(" ")}
        >
          <div className="flex items-center justify-between px-3 py-3 lg:hidden">
            <span className="text-sm text-white/80">Menú</span>
            <button type="button" className="p-1 text-white" onClick={() => setSidebarOpen(false)} aria-label="Cerrar">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {visibleNav.map((group) => {
              const Icon = group.icon;
              if (group.to && !group.items) {
                return (
                  <NavLink
                    key={group.id}
                    to={group.to}
                    onClick={() => setSidebarOpen(false)}
                    className={({ isActive }) => linkClass(isActive)}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    {group.label}
                  </NavLink>
                );
              }

              const opened = openGroups[group.id] ?? true;
              return (
                <div key={group.id}>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-white/80 hover:bg-white/8"
                    onClick={() => toggleGroup(group.id)}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="flex-1">{group.label}</span>
                    <ChevronDown className={`h-4 w-4 transition ${opened ? "rotate-0" : "-rotate-90"}`} />
                  </button>
                  {opened ? (
                    <div className="mb-1 ml-4 space-y-0.5 border-l border-white/10 pl-2">
                      {group.items?.map((item) => (
                        <NavLink
                          key={item.to}
                          to={item.to}
                          end={item.end}
                          onClick={() => setSidebarOpen(false)}
                          className={({ isActive }) => linkClass(isActive)}
                        >
                          {item.label}
                        </NavLink>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </nav>
          <p className="px-4 pb-4 text-[11px] text-white/40">Fondo Emprender · tilapia Biofloc</p>
        </aside>

        <main className="min-h-[calc(100vh-3.5rem)] min-w-0 flex-1 px-4 py-6 sm:px-8">
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
