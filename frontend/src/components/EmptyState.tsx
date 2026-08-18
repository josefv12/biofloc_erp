type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--bf-border)] bg-white px-6 py-10 text-center">
      <p className="text-sm font-medium text-[var(--bf-ink)]">{title}</p>
      {description ? <p className="mt-1 text-sm text-[var(--bf-muted)]">{description}</p> : null}
    </div>
  );
}
