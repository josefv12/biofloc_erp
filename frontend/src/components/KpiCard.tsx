import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type KpiCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  /** Texto nativo de ayuda (tooltip). No sustituye el valor. */
  title?: string;
  to?: string;
  emphasize?: boolean;
};

export function KpiCard({ label, value, hint, title, to, emphasize = false }: KpiCardProps) {
  const nd = value === "N/D";
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--bf-muted)]">{label}</p>
      <p
        className={`mt-2 font-display text-2xl font-semibold ${
          nd ? "text-[var(--bf-muted)]" : emphasize ? "text-amber-800" : "text-[var(--bf-ink)]"
        }`}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--bf-muted)]">{hint}</p> : null}
    </>
  );

  const className = [
    "block rounded-2xl border bg-white px-4 py-4 shadow-[0_1px_2px_rgba(16,40,33,0.04),0_8px_24px_rgba(16,40,33,0.05)] transition-all duration-150 bf-enter",
    emphasize ? "border-amber-200" : "border-[var(--bf-border)]",
    "hover:-translate-y-0.5 hover:border-[var(--bf-accent)] hover:shadow-[0_10px_28px_rgba(16,40,33,0.08)]",
    to ? "hover:bg-[var(--bf-chip)]" : "",
  ].join(" ");

  if (to) {
    return (
      <Link to={to} className={className} title={title}>
        {body}
      </Link>
    );
  }

  return (
    <article className={className} title={title}>
      {body}
    </article>
  );
}
