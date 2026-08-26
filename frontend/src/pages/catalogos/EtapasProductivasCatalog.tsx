import { useQuery } from "@tanstack/react-query";
import { DataTable } from "../../components/DataTable";
import { ErrorAlert } from "../../components/ErrorAlert";
import { LoadingState } from "../../components/LoadingState";
import { StatusBadge } from "../../components/StatusBadge";
import { listEtapasProductivas } from "../../api/production";
import { apiErrorMessage } from "../../utils/apiError";

export function EtapasProductivasCatalog() {
  const query = useQuery({
    queryKey: ["etapas-productivas", "catalog"],
    queryFn: () => listEtapasProductivas(false),
  });

  return (
    <section className="mb-8">
      <div className="mb-3">
        <h2 className="font-display text-lg font-semibold text-[var(--bf-ink)]">Etapas productivas</h2>
        <p className="mt-1 max-w-3xl text-sm text-[var(--bf-muted)]">
          Catálogo de consulta. El contrato actual solo expone GET: no hay alta ni edición desde esta
          pantalla. Las referencias de producción y de agua usan estas etapas.
        </p>
      </div>
      {query.isLoading ? <LoadingState /> : null}
      {query.isError ? <ErrorAlert message={apiErrorMessage(query.error)} /> : null}
      {query.data ? (
        <DataTable
          rows={query.data}
          rowKey={(row) => row.id}
          empty="No hay etapas productivas."
          columns={[
            { key: "nombre", header: "Nombre" },
            { key: "descripcion", header: "Descripción", render: (row) => row.descripcion || "—" },
            { key: "orden", header: "Orden", render: (row) => String(row.orden) },
            {
              key: "activo",
              header: "Estado",
              render: (row) => (
                <StatusBadge label={row.activo ? "Activo" : "Inactivo"} tone={row.activo ? "ok" : "neutral"} />
              ),
            },
          ]}
        />
      ) : null}
    </section>
  );
}
