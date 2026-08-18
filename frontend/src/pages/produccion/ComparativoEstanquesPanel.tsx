import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getComparativoEstanques } from "../../api/analisis";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { apiErrorMessage } from "../../utils/apiError";
import { formatCop, formatEstado, formatNumber } from "../../utils/format";
import type { EstanqueComparativo } from "../../types/analisis";

/**
 * Nivel granja: un renglón por estanque con los indicadores de su lote activo.
 * Todo lo calcula el endpoint comparativo; aquí no se agrega nada.
 */
export function ComparativoEstanquesPanel({ soloActivos }: { soloActivos: boolean }) {
  const query = useQuery({
    queryKey: ["analisis-estanques", soloActivos],
    queryFn: () => getComparativoEstanques(soloActivos),
  });

  if (query.isLoading) return <LoadingState label="Cargando comparativo analítico…" />;
  if (query.isError) return <ErrorAlert message={apiErrorMessage(query.error)} />;
  const data = query.data;
  if (!data) return null;

  const { resumen, definiciones } = data;
  const numero = (valor: string | number | null, digitos = 3) =>
    valor === null ? "N/D" : formatNumber(valor, { maximumFractionDigits: digitos });

  return (
    <section className="mb-6 space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Estanques con lote activo"
          value={`${formatNumber(resumen.estanques_con_lote_activo)} de ${formatNumber(resumen.estanques)}`}
        />
        <KpiCard label="Población estimada" value={formatNumber(resumen.poblacion_estimada)} />
        <KpiCard
          label="Biomasa actual (kg)"
          value={numero(resumen.biomasa_actual_kg)}
          hint={
            resumen.lotes_sin_biomasa > 0
              ? `${resumen.lotes_sin_biomasa} lote(s) sin biometría no aportan biomasa.`
              : definiciones.biomasa_granja
          }
        />
        <KpiCard label="Peces sembrados" value={formatNumber(resumen.peces_sembrados)} />
        <KpiCard
          label="Supervivencia %"
          value={numero(resumen.supervivencia_porcentaje, 2)}
          hint={definiciones.supervivencia_granja}
        />
        <KpiCard
          label="Mortalidad %"
          value={numero(resumen.mortalidad_porcentaje, 2)}
          hint={definiciones.mortalidad_granja}
        />
        <KpiCard label="Mortalidad acumulada" value={formatNumber(resumen.mortalidad_acumulada)} />
        <KpiCard
          label="FCA de granja"
          value={numero(resumen.fca, 4)}
          hint={`${definiciones.fca_granja} Lotes con FCA disponible: ${resumen.lotes_con_fca}.`}
        />
        <KpiCard label="Producción cosechada (kg)" value={numero(resumen.peso_cosechado_kg)} />
        <KpiCard label="Peces cosechados" value={formatNumber(resumen.peces_cosechados)} />
        <KpiCard label="Ingresos de lotes activos" value={formatCop(resumen.ingresos_lotes_activos)} />
        <KpiCard
          label="Gastos directos de lotes activos"
          value={formatCop(resumen.gastos_directos_lotes_activos)}
          hint="No representa el costo total de producción."
        />
      </div>

      <DataTable
        rows={data.estanques}
        rowKey={(row) => row.estanque_id}
        empty="No hay estanques para comparar."
        columns={[
          { key: "codigo", header: "Estanque" },
          {
            key: "lote",
            header: "Lote activo",
            render: (row: EstanqueComparativo) =>
              row.lote_id ? (
                <Link
                  to={`/produccion/lotes/${row.lote_id}?tab=analisis`}
                  className="font-medium text-[var(--bf-accent)] hover:underline"
                >
                  {row.lote_codigo}
                </Link>
              ) : (
                <span className="text-[var(--bf-muted)]">Sin lote activo</span>
              ),
          },
          { key: "especie", header: "Especie", render: (row) => row.especie ?? "N/D" },
          {
            key: "semana",
            header: "Semana",
            render: (row) => (row.semana_cultivo === null ? "N/D" : String(row.semana_cultivo)),
          },
          {
            key: "poblacion",
            header: "Población",
            render: (row) => (row.poblacion_estimada === null ? "N/D" : formatNumber(row.poblacion_estimada)),
          },
          { key: "peso", header: "Peso (g)", render: (row) => numero(row.peso_promedio_g) },
          { key: "crecimiento", header: "Crecimiento (g)", render: (row) => numero(row.ganancia_peso_g) },
          { key: "biomasa", header: "Biomasa (kg)", render: (row) => numero(row.biomasa_actual_kg) },
          {
            key: "productividad",
            header: "Productividad Δ kg",
            render: (row) => numero(row.productividad?.ganancia_biomasa_kg ?? null),
          },
          {
            key: "alimento",
            header: "Alimento real (kg)",
            render: (row) => numero(row.alimento_real_acumulado_kg),
          },
          {
            key: "supervivencia",
            header: "Superv. %",
            render: (row) => numero(row.supervivencia_porcentaje, 2),
          },
          {
            key: "mortalidad",
            header: "Mort. %",
            render: (row) => numero(row.mortalidad_porcentaje, 2),
          },
          {
            key: "fca",
            header: "Eficiencia · FCA",
            render: (row) =>
              row.fca_disponible ? (
                formatNumber(row.fca, { maximumFractionDigits: 4 })
              ) : (
                <span className="text-[var(--bf-muted)]" title={row.fca_motivo ?? undefined}>
                  N/D
                </span>
              ),
          },
          {
            key: "biofloc",
            header: "Biofloc",
            render: (row) =>
              row.lote_id === null ? (
                "N/D"
              ) : (
                <StatusBadge label={formatEstado(row.estado_biofloc)} tone="neutral" />
              ),
          },
          {
            key: "agua",
            header: "Agua",
            render: (row) => {
              if (row.lote_id === null) return "N/D";
              if (row.agua_parametros_medidos === 0) return <span className="text-[var(--bf-muted)]">Sin medir</span>;
              if (row.agua_parametros_fuera_de_rango === null) {
                return <span className="text-[var(--bf-muted)]">Sin referencia</span>;
              }
              return row.agua_parametros_fuera_de_rango > 0 ? (
                <StatusBadge
                  label={`${row.agua_parametros_fuera_de_rango} fuera de rango`}
                  tone="danger"
                />
              ) : (
                <StatusBadge label="Dentro del rango" tone="ok" />
              );
            },
          },
        ]}
      />

      <p className="text-xs text-[var(--bf-muted)]">{definiciones.alcance}</p>
    </section>
  );
}
