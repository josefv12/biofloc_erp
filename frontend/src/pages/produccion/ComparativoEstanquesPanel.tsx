import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getComparativoEstanques } from "../../api/analisis";
import { DataTable } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { ErrorAlert } from "../../components/ErrorAlert";
import { KpiCard } from "../../components/KpiCard";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { pathFichaEstanque } from "./fichaPaths";
import { apiErrorMessage } from "../../utils/apiError";
import { formatEstado, formatNumber } from "../../utils/format";
import type { EstanqueComparativo } from "../../types/analisis";
import { FCA_HINT_ECONOMICO, FCA_LABEL } from "../../utils/fcaPresentacion";

/**
 * Nivel granja: un renglón por estanque con los indicadores de su lote activo.
 * Todo lo calcula el endpoint comparativo; aquí no se agrega nada.
 */
export function ComparativoEstanquesPanel({
  soloActivos,
  mostrarResumen = true,
}: {
  soloActivos: boolean;
  mostrarResumen?: boolean;
}) {
  const [busqueda, setBusqueda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState<"todos" | "ocupado" | "disponible">("todos");
  const [filtroEspecie, setFiltroEspecie] = useState("todas");
  const [filtroEtapa, setFiltroEtapa] = useState("todas");

  const query = useQuery({
    queryKey: ["analisis-estanques", soloActivos],
    queryFn: () => getComparativoEstanques(soloActivos),
  });

  const filas = useMemo(() => {
    const todas = query.data?.estanques ?? [];
    const q = busqueda.trim().toLowerCase();
    return todas.filter((row) => {
      if (filtroEstado === "ocupado" && !row.lote_id) return false;
      if (filtroEstado === "disponible" && row.lote_id) return false;
      if (filtroEspecie !== "todas" && (row.especie ?? "N/D") !== filtroEspecie) return false;
      if (filtroEtapa !== "todas" && (row.etapa ?? "N/D") !== filtroEtapa) return false;
      if (!q) return true;
      const hay = [row.codigo, row.nombre, row.lote_codigo, row.especie, row.etapa]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [query.data, busqueda, filtroEstado, filtroEspecie, filtroEtapa]);

  const especies = useMemo(
    () => Array.from(new Set((query.data?.estanques ?? []).map((row) => row.especie ?? "N/D"))),
    [query.data],
  );
  const etapas = useMemo(
    () => Array.from(new Set((query.data?.estanques ?? []).map((row) => row.etapa ?? "N/D"))),
    [query.data],
  );

  if (query.isLoading) return <LoadingState label="Cargando comparativo analítico…" />;
  if (query.isError) return <ErrorAlert message={apiErrorMessage(query.error)} />;
  const data = query.data;
  if (!data) return null;

  const { resumen, definiciones } = data;
  const numero = (valor: string | number | null, digitos = 3) =>
    valor === null ? "N/D" : formatNumber(valor, { maximumFractionDigits: digitos });
  const vacio = data.estanques.length === 0;

  return (
    <section className="mb-6 space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Comparación de estanques</h2>
        <p className="text-sm text-[var(--bf-muted)]">
          Indicadores del lote activo, calculados por el API. El FCA acumulado pertenece al lote,
          no al estanque. N/D no se convierte en 0. No hay FCA de granja: no se promedian lotes.
        </p>
      </div>
      {mostrarResumen && !vacio ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Estanques con lote activo"
            value={`${formatNumber(resumen.estanques_con_lote_activo)} de ${formatNumber(resumen.estanques)}`}
          />
          <KpiCard
            label="Población estimada"
            value={resumen.estanques_con_lote_activo === 0 ? "N/D" : formatNumber(resumen.poblacion_estimada)}
          />
          <KpiCard label="Biomasa actual (kg)" value={numero(resumen.biomasa_actual_kg)} />
          <KpiCard label="Supervivencia %" value={numero(resumen.supervivencia_porcentaje, 2)} />
        </div>
      ) : null}

      {vacio ? (
        <EmptyState
          title="Sin estanques registrados"
          description="Cuando existan estanques, aquí se comparan población, biomasa, supervivencia y FCA acumulado del lote activo de cada estanque."
        />
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <input
              className="bf-input"
              placeholder="Buscar código, lote o especie"
              value={busqueda}
              onChange={(event) => setBusqueda(event.target.value)}
            />
            <select
              className="bf-input"
              value={filtroEstado}
              onChange={(event) => setFiltroEstado(event.target.value as typeof filtroEstado)}
            >
              <option value="todos">Todos los estados</option>
              <option value="ocupado">Ocupados</option>
              <option value="disponible">Disponibles</option>
            </select>
            <select className="bf-input" value={filtroEspecie} onChange={(event) => setFiltroEspecie(event.target.value)}>
              <option value="todas">Todas las especies</option>
              {especies.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
            <select className="bf-input" value={filtroEtapa} onChange={(event) => setFiltroEtapa(event.target.value)}>
              <option value="todas">Todas las etapas</option>
              {etapas.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
          </div>
          <DataTable
            rows={filas}
            rowKey={(row) => row.estanque_id}
            empty="No hay estanques que coincidan con el filtro."
            columns={[
              {
                key: "codigo",
                header: "Código",
                render: (row: EstanqueComparativo) => (
                  <Link
                    to={pathFichaEstanque(row.estanque_id, { loteId: row.lote_id })}
                    className="font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    {row.codigo}
                  </Link>
                ),
              },
              {
                key: "estado",
                header: "Estado",
                render: (row) => (
                  <StatusBadge label={row.lote_id ? "Ocupado" : "Disponible"} tone={row.lote_id ? "ok" : "neutral"} />
                ),
              },
              { key: "especie", header: "Especie", render: (row) => row.especie ?? "N/D" },
              { key: "etapa", header: "Etapa", render: (row) => row.etapa ?? "N/D" },
              {
                key: "lote",
                header: "Lote",
                render: (row: EstanqueComparativo) =>
                  row.lote_id ? (
                    <Link
                      to={pathFichaEstanque(row.estanque_id, { loteId: row.lote_id })}
                      className="font-medium text-[var(--bf-accent)] hover:underline"
                    >
                      {row.lote_codigo}
                    </Link>
                  ) : (
                    <span className="text-[var(--bf-muted)]">N/D</span>
                  ),
              },
              {
                key: "semana",
                header: "Semana",
                render: (row) => (row.semana_cultivo === null ? "N/D" : String(row.semana_cultivo)),
              },
              { key: "peso", header: "Peso (g)", render: (row) => numero(row.peso_promedio_g) },
              { key: "biomasa", header: "Biomasa (kg)", render: (row) => numero(row.biomasa_actual_kg) },
              {
                key: "poblacion",
                header: "Población",
                render: (row) => (row.poblacion_estimada === null ? "N/D" : formatNumber(row.poblacion_estimada)),
              },
              {
                key: "supervivencia",
                header: "Supervivencia",
                render: (row) => numero(row.supervivencia_porcentaje, 2),
              },
              {
                key: "fca",
                header: FCA_LABEL,
                render: (row) =>
                  row.fca_disponible ? (
                    <span title={`${FCA_HINT_ECONOMICO} Corresponde al lote activo del estanque.`}>
                      {formatNumber(row.fca, { maximumFractionDigits: 4 })}
                    </span>
                  ) : (
                    <span
                      className="text-[var(--bf-muted)]"
                      title={row.fca_motivo ?? undefined}
                    >
                      N/D
                    </span>
                  ),
              },
              {
                key: "biofloc",
                header: "Biofloc",
                render: (row) =>
                  row.lote_id === null ? "N/D" : <StatusBadge label={formatEstado(row.estado_biofloc)} tone="neutral" />,
              },
              {
                key: "agua",
                header: "Agua",
                render: (row) => {
                  if (row.lote_id === null) return "N/D";
                  if (row.agua_parametros_medidos === 0) {
                    return <span className="text-[var(--bf-muted)]">SIN DATOS</span>;
                  }
                  if (row.agua_parametros_fuera_de_rango === null) {
                    return <span className="text-[var(--bf-muted)]">SIN REFERENCIA</span>;
                  }
                  return row.agua_parametros_fuera_de_rango > 0 ? (
                    <StatusBadge label={`${row.agua_parametros_fuera_de_rango} FUERA_RANGO`} tone="neutral" />
                  ) : (
                    <StatusBadge label="DENTRO_RANGO" tone="neutral" />
                  );
                },
              },
              {
                key: "entrar",
                header: "",
                render: (row) => (
                  <Link
                    to={pathFichaEstanque(row.estanque_id, { loteId: row.lote_id })}
                    className="bf-btn-primary !py-1 text-xs"
                  >
                    Ver estanque
                  </Link>
                ),
              },
            ]}
          />
        </>
      )}

      {vacio ? null : <p className="text-xs text-[var(--bf-muted)]">{definiciones.alcance}</p>}
    </section>
  );
}
