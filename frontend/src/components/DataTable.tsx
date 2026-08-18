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
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "No hay registros.",
  onRowClick,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={empty} />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--bf-border)] bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-[var(--bf-border)] bg-[var(--bf-table-head)]">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-4 py-2.5 font-medium text-[var(--bf-muted)] ${column.className ?? ""}`}
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
              className={`border-b border-[var(--bf-border)] last:border-0 ${
                onRowClick ? "cursor-pointer hover:bg-[var(--bf-chip)]" : ""
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
