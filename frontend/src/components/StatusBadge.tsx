type Tone = "neutral" | "ok" | "warn" | "danger" | "info";

const TONES: Record<Tone, string> = {
  neutral: "bg-[var(--bf-chip)] text-[var(--bf-ink)] ring-1 ring-[var(--bf-border)]",
  ok: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
  warn: "bg-amber-50 text-amber-900 ring-1 ring-amber-200/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
  danger: "bg-red-50 text-red-800 ring-1 ring-red-200/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
  info: "bg-sky-50 text-sky-900 ring-1 ring-sky-200/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
};

type StatusBadgeProps = {
  label: string;
  tone?: Tone;
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${TONES[tone]}`}
    >
      {label}
    </span>
  );
}
