import type { ReactNode } from "react";

type ModalProps = {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  size?: "md" | "lg";
};

export function Modal({ open, title, children, onClose, size = "md" }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-[var(--bf-ink)]/40"
        aria-label="Cerrar"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`relative max-h-[90vh] w-full overflow-y-auto rounded-xl border border-[var(--bf-border)] bg-white p-5 shadow-lg ${
          size === "lg" ? "max-w-3xl" : "max-w-lg"
        }`}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 id="modal-title" className="font-display text-lg font-semibold text-[var(--bf-ink)]">
            {title}
          </h2>
          <button type="button" className="bf-btn-secondary !px-2 !py-1 text-xs" onClick={onClose}>
            Cerrar
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
