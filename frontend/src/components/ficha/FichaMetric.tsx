import type { ReactNode } from "react";

export function FichaLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--bf-accent)]">{children}</p>
  );
}

export function FichaBadge({
  tone = "neutral",
  children,
}: {
  tone?: "ok" | "warn" | "danger" | "neutral";
  children: ReactNode;
}) {
  const tones = {
    ok: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-100",
    warn: "bg-amber-50 text-amber-800 ring-1 ring-amber-100",
    danger: "bg-red-50 text-red-800 ring-1 ring-red-100",
    neutral: "bg-[var(--bf-chip)] text-[var(--bf-ink)] ring-1 ring-[var(--bf-border)]",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function FichaMetric({
  label,
  value,
  unit,
  sub,
  badge,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  sub?: string;
  badge?: ReactNode;
}) {
  return (
    <div>
      <FichaLabel>{label}</FichaLabel>
      <div className="flex flex-wrap items-baseline gap-1">
        <span className="text-2xl font-bold text-[var(--bf-ink)]">{value}</span>
        {unit ? <span className="text-sm text-[var(--bf-muted)]">{unit}</span> : null}
        {badge}
      </div>
      {sub ? <p className="mt-0.5 text-xs italic text-[var(--bf-muted)]">{sub}</p> : null}
    </div>
  );
}

export function FichaSectionHeader({ title, note }: { title: string; note?: string }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h3 className="text-[13px] font-bold uppercase tracking-wide text-[var(--bf-accent)]">{title}</h3>
      {note ? <span className="text-xs text-[var(--bf-muted)]">{note}</span> : null}
    </div>
  );
}

export function FichaCard({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 rounded-2xl border border-[var(--bf-border)] bg-white p-5 shadow-[0_1px_2px_rgba(16,40,33,0.04),0_8px_24px_rgba(16,40,33,0.04)] last:mb-0">{children}</div>
  );
}
