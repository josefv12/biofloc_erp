import type { ReactNode } from "react";

type ModalProps = {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  size?: "md" | "lg";
  footer?: ReactNode;
};

export function Modal({ open, title, children, onClose, size = "md", footer }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-[var(--bf-ink)]/45 backdrop-blur-[3px]"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`relative flex max-h-[90vh] w-full flex-col overflow-hidden rounded-2xl border border-[var(--bf-border)] bg-white shadow-[0_24px_60px_rgba(16,40,33,0.18)] ${
          size === "lg" ? "max-w-3xl" : "max-w-lg"
        }`}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-[var(--bf-border)] px-5 py-4">
          <h2 id="modal-title" className="font-display text-lg font-semibold text-[var(--bf-ink)]">
            {title}
          </h2>
          <button type="button" className="bf-btn-secondary !px-2 !py-1 text-xs" onClick={onClose}>
            Cerrar
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer ? (
          <div className="flex shrink-0 justify-end gap-2 border-t border-[var(--bf-border)] px-5 py-3">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}
