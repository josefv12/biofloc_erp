import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type KpiCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  to?: string;
  emphasize?: boolean;
};

export function KpiCard({ label, value, hint, to, emphasize = false }: KpiCardProps) {
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--bf-muted)]">{label}</p>
      <p
        className={`mt-2 font-display text-2xl font-semibold ${
          emphasize ? "text-amber-800" : "text-[var(--bf-ink)]"
        }`}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--bf-muted)]">{hint}</p> : null}
    </>
  );

  const className = [
    "block rounded-xl border bg-white px-4 py-4 shadow-[0_1px_0_rgba(22,51,45,0.04)]",
    emphasize ? "border-amber-200" : "border-[var(--bf-border)]",
    to ? "transition-colors hover:border-[var(--bf-accent)] hover:bg-[var(--bf-chip)]" : "",
  ].join(" ");

  if (to) {
    return (
      <Link to={to} className={className}>
        {body}
      </Link>
    );
  }

  return <article className={className}>{body}</article>;
}
