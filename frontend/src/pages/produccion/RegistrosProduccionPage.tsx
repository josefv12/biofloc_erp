import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { PageHeader } from "../../components/PageHeader";
import { listBiometrias, listCosechas, listLotes, listMortalidades } from "../../api/production";
import { pathFichaEstanque } from "./fichaPaths";
import { apiErrorMessage } from "../../utils/apiError";
import { formatDateTime, formatNumber } from "../../utils/format";
import type { Biometria, Cosecha, Mortalidad } from "../../types/production";

function useLotesMap() {
  const query = useQuery({ queryKey: ["lotes"], queryFn: () => listLotes() });
  const map = new Map((query.data ?? []).map((lote) => [lote.id, lote]));
  return { query, map };
}

export function BiometriasListPage() {
  const { query: lotesQuery, map } = useLotesMap();
  const query = useQuery({ queryKey: ["biometrias"], queryFn: () => listBiometrias() });
  return (
    <div className="bf-enter">
      <PageHeader
        title="Biometrías"
        description="Registros productivos de muestreo. Entre al estanque para ver el análisis del lote."
      />
      {query.isLoading || lotesQuery.isLoading ? <LoadingState label="Cargando biometrías…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: Biometria) => row.id}
          empty="Sin biometrías registradas."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "lote",
              header: "Lote",
              render: (row) => map.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
            },
            {
              key: "muestra",
              header: "Muestra",
              render: (row) => formatNumber(row.cantidad_muestra),
            },
            {
              key: "peso",
              header: "Peso total (g)",
              render: (row) => formatNumber(row.peso_total_muestra_g, { maximumFractionDigits: 3 }),
            },
            {
              key: "ver",
              header: "",
              render: (row) => {
                const lote = map.get(row.lote_id);
                if (!lote) return "—";
                return (
                  <Link
                    to={pathFichaEstanque(lote.estanque_id, { loteId: lote.id, tab: "produccion" })}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Ver estanque
                  </Link>
                );
              },
            },
          ]}
        />
      ) : null}
    </div>
  );
}

export function MortalidadesListPage() {
  const { query: lotesQuery, map } = useLotesMap();
  const query = useQuery({ queryKey: ["mortalidades"], queryFn: () => listMortalidades() });
  return (
    <div className="bf-enter">
      <PageHeader
        title="Mortalidades"
        description="Registros de mortalidad. La población la calcula el backend; aquí solo se listan los eventos."
      />
      {query.isLoading || lotesQuery.isLoading ? <LoadingState label="Cargando mortalidades…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: Mortalidad) => row.id}
          empty="Sin mortalidades registradas."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "lote",
              header: "Lote",
              render: (row) => map.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
            },
            { key: "cantidad", header: "Cantidad", render: (row) => formatNumber(row.cantidad) },
            { key: "causa", header: "Causa", render: (row) => row.causa || "—" },
            {
              key: "ver",
              header: "",
              render: (row) => {
                const lote = map.get(row.lote_id);
                if (!lote) return "—";
                return (
                  <Link
                    to={pathFichaEstanque(lote.estanque_id, { loteId: lote.id, tab: "produccion" })}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Ver estanque
                  </Link>
                );
              },
            },
          ]}
        />
      ) : null}
    </div>
  );
}

export function CosechasListPage() {
  const { query: lotesQuery, map } = useLotesMap();
  const query = useQuery({ queryKey: ["cosechas"], queryFn: () => listCosechas() });
  return (
    <div className="bf-enter">
      <PageHeader
        title="Cosechas"
        description="Registros de cosecha. El peso y la población de cada lote salen del análisis del servidor."
      />
      {query.isLoading || lotesQuery.isLoading ? <LoadingState label="Cargando cosechas…" /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row: Cosecha) => row.id}
          empty="Sin cosechas registradas."
          columns={[
            { key: "fecha", header: "Fecha", render: (row) => formatDateTime(row.fecha_hora) },
            {
              key: "lote",
              header: "Lote",
              render: (row) => map.get(row.lote_id)?.codigo ?? `#${row.lote_id}`,
            },
            { key: "peces", header: "Peces", render: (row) => formatNumber(row.cantidad_peces) },
            {
              key: "peso",
              header: "Peso total (kg)",
              render: (row) => formatNumber(row.peso_total_kg, { maximumFractionDigits: 3 }),
            },
            {
              key: "ver",
              header: "",
              render: (row) => {
                const lote = map.get(row.lote_id);
                if (!lote) return "—";
                return (
                  <Link
                    to={pathFichaEstanque(lote.estanque_id, { loteId: lote.id, tab: "produccion" })}
                    className="text-xs font-medium text-[var(--bf-accent)] hover:underline"
                  >
                    Ver estanque
                  </Link>
                );
              },
            },
          ]}
        />
      ) : null}
    </div>
  );
}
