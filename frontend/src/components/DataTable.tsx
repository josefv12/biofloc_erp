import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  className?: string;
  render?: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  empty?: string;
  onRowClick?: (row: T) => void;
  /** Si hay más filas, aparece scroll vertical interno y el encabezado queda fijo. */
  maxVisibleRows?: number;
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "No hay registros.",
  onRowClick,
  maxVisibleRows,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={empty} />;
  }

  const scrollVertical = maxVisibleRows != null && rows.length > maxVisibleRows;
  const maxHeight = scrollVertical ? `calc(2.75rem + ${maxVisibleRows} * 2.85rem)` : undefined;

  return (
    <div
      className={`rounded-2xl border border-[var(--bf-border)] bg-white shadow-[0_1px_2px_rgba(16,40,33,0.04),0_8px_24px_rgba(16,40,33,0.05)] ${
        scrollVertical ? "overflow-auto" : "overflow-x-auto"
      }`}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-[var(--bf-border)] bg-[var(--bf-table-head)] sticky top-0 z-10">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--bf-muted)] ${column.className ?? ""}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={`border-b border-[var(--bf-border)]/80 last:border-0 transition-colors duration-100 hover:bg-[var(--bf-chip)] ${
                onRowClick ? "cursor-pointer" : ""
              }`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((column) => (
                <td key={column.key} className={`whitespace-nowrap px-4 py-3 text-[var(--bf-ink)] ${column.className ?? ""}`}>
                  {column.render
                    ? column.render(row)
                    : String((row as Record<string, unknown>)[column.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
