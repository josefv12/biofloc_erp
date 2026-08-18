import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function NotFoundPage() {
  return (
    <div>
      <PageHeader title="No encontrado" description="La dirección no corresponde a ninguna pantalla del ERP." />
      <EmptyState title="Página no encontrada" description="Revise el enlace o vuelva al dashboard." />
      <Link to="/dashboard" className="bf-btn-primary mt-4 inline-flex">
        Ir al dashboard
      </Link>
    </div>
  );
}
