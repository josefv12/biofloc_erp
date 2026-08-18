type Tone = "neutral" | "ok" | "warn" | "danger" | "info";

const TONES: Record<Tone, string> = {
  neutral: "bg-[var(--bf-chip)] text-[var(--bf-ink)]",
  ok: "bg-emerald-50 text-emerald-800",
  warn: "bg-amber-50 text-amber-900",
  danger: "bg-red-50 text-red-800",
  info: "bg-sky-50 text-sky-900",
};

type StatusBadgeProps = {
  label: string;
  tone?: Tone;
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {label}
    </span>
  );
}
