interface ResultsTableProps {
  rows: Record<string, unknown>[];
}

// Compact table of the rows returned by the final SPL. Renders an empty-state
// note when the query matched nothing.
export default function ResultsTable({ rows }: ResultsTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-dim text-sm font-mono">
        No rows returned for this query.
      </p>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="bg-elevated text-dim uppercase tracking-widest">
            {columns.map((col) => (
              <th key={col} className="text-left px-3 py-2 font-semibold">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-border">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-moat whitespace-nowrap">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
