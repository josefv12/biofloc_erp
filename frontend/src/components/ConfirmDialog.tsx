type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-[var(--bf-ink)]/45 backdrop-blur-[3px]"
        aria-label="Cerrar"
        onClick={onCancel}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="relative w-full max-w-md rounded-2xl border border-[var(--bf-border)] bg-white p-6 shadow-[0_24px_60px_rgba(16,40,33,0.18)]"
      >
        <h2 id="confirm-title" className="font-display text-lg font-semibold text-[var(--bf-ink)]">
          {title}
        </h2>
        {description ? <p className="mt-2 text-sm text-[var(--bf-muted)]">{description}</p> : null}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="bf-btn-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className="bf-btn-primary" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
