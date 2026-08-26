type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--bf-border)] bg-[var(--bf-header)] px-6 py-12 text-center">
      <p className="font-display text-sm font-semibold text-[var(--bf-ink)]">{title}</p>
      {description ? <p className="mx-auto mt-1 max-w-md text-sm text-[var(--bf-muted)]">{description}</p> : null}
    </div>
  );
}
