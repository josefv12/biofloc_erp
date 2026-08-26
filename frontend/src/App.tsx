import { lazy, Suspense, type ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { LoadingState } from "./components/LoadingState";

const page = <T extends object>(loader: () => Promise<T>, name: keyof T) =>
  lazy(() => loader().then((module) => ({ default: module[name] as ComponentType })));
const DashboardPage = page(() => import("./pages/DashboardPage"), "DashboardPage");
const PerfilPage = page(() => import("./pages/PerfilPage"), "PerfilPage");
const EstanquesPage = page(() => import("./pages/produccion/EstanquesPage"), "EstanquesPage");
const EstanqueFichaPage = page(() => import("./pages/produccion/EstanqueFichaPage"), "EstanqueFichaPage");
const LotesPage = page(() => import("./pages/produccion/LotesPage"), "LotesPage");
const LoteFichaPage = page(() => import("./pages/produccion/LoteFichaPage"), "LoteFichaPage");
const BiometriasListPage = page(() => import("./pages/produccion/RegistrosProduccionPage"), "BiometriasListPage");
const MortalidadesListPage = page(() => import("./pages/produccion/RegistrosProduccionPage"), "MortalidadesListPage");
const CosechasListPage = page(() => import("./pages/produccion/RegistrosProduccionPage"), "CosechasListPage");
const AguaPage = page(() => import("./pages/operacion/AguaPage"), "AguaPage");
const BioflocPage = page(() => import("./pages/operacion/BioflocPage"), "BioflocPage");
const AlimentacionPage = page(() => import("./pages/operacion/AlimentacionPage"), "AlimentacionPage");
const InventarioPage = page(() => import("./pages/inventario/InventarioPage"), "InventarioPage");
const MovimientosPage = page(() => import("./pages/inventario/MovimientosPage"), "MovimientosPage");
const ComprasPage = page(() => import("./pages/compras/ComprasPage"), "ComprasPage");
const CompraDetallePage = page(() => import("./pages/compras/CompraDetallePage"), "CompraDetallePage");
const FinanzasPage = page(() => import("./pages/finanzas/FinanzasPage"), "FinanzasPage");
const GastosPage = page(() => import("./pages/finanzas/GastosPage"), "GastosPage");
const VentasPage = page(() => import("./pages/finanzas/VentasPage"), "VentasPage");
const VentaDetallePage = page(() => import("./pages/finanzas/VentaDetallePage"), "VentaDetallePage");
const EquiposPage = page(() => import("./pages/equipos/EquiposPage"), "EquiposPage");
const MantenimientosFallasPage = page(() => import("./pages/equipos/MantenimientosFallasPage"), "MantenimientosFallasPage");
const EnergiaPage = page(() => import("./pages/equipos/EnergiaPage"), "EnergiaPage");
const AlarmasPage = page(() => import("./pages/alarmas/AlarmasPage"), "AlarmasPage");
const AlarmaDetallePage = page(() => import("./pages/alarmas/AlarmaDetallePage"), "AlarmaDetallePage");
const ReportesPage = page(() => import("./pages/reportes/ReportesPage"), "ReportesPage");
const CatalogosPage = page(() => import("./pages/catalogos/CatalogosPage"), "CatalogosPage");
const UsuariosPage = page(() => import("./pages/admin/UsuariosPage"), "UsuariosPage");
const NotFoundPage = page(() => import("./pages/NotFoundPage"), "NotFoundPage");

export function App() {
  return (
    <Suspense fallback={<LoadingState label="Cargando módulo…" />}>
      <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/perfil" element={<PerfilPage />} />
        <Route path="/produccion/estanques/:id" element={<EstanqueFichaPage />} />
        <Route path="/produccion/estanques" element={<EstanquesPage />} />
        <Route path="/produccion/lotes/:id" element={<LoteFichaPage />} />
        <Route path="/produccion/lotes" element={<LotesPage />} />
        <Route path="/produccion/biometrias" element={<BiometriasListPage />} />
        <Route path="/produccion/mortalidades" element={<MortalidadesListPage />} />
        <Route path="/produccion/cosechas" element={<CosechasListPage />} />
        <Route path="/operacion/agua" element={<AguaPage />} />
        <Route path="/operacion/biofloc" element={<BioflocPage />} />
        <Route path="/operacion/alimentacion" element={<AlimentacionPage />} />
        <Route path="/inventario/movimientos" element={<MovimientosPage />} />
        <Route path="/inventario" element={<InventarioPage />} />
        <Route path="/compras/:id" element={<CompraDetallePage />} />
        <Route path="/compras" element={<ComprasPage />} />
        <Route path="/finanzas/gastos" element={<GastosPage />} />
        <Route path="/finanzas/ventas/:id" element={<VentaDetallePage />} />
        <Route path="/finanzas/ventas" element={<VentasPage />} />
        <Route path="/finanzas" element={<FinanzasPage />} />
        <Route path="/equipos/mantenimientos" element={<MantenimientosFallasPage />} />
        <Route path="/equipos" element={<EquiposPage />} />
        <Route path="/energia" element={<EnergiaPage />} />
        <Route path="/alarmas/:id" element={<AlarmaDetallePage />} />
        <Route path="/alarmas" element={<AlarmasPage />} />
        <Route path="/reportes" element={<ReportesPage />} />
        <Route path="/catalogos" element={<CatalogosPage />} />
        <Route
          path="/admin/usuarios"
          element={
            <RequireRole roles={["ADMINISTRADOR"]}>
              <UsuariosPage />
            </RequireRole>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
