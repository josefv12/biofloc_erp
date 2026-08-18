type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = "Cargando…" }: LoadingStateProps) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-[var(--bf-muted)]" role="status">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--bf-border)] border-t-[var(--bf-accent)]"
        aria-hidden
      />
      {label}
    </div>
  );
}
