import type { CleaningOperation } from "../../types/api";

export function CleaningOperationList({ operations }: { operations: CleaningOperation[] }) {
  if (!operations || operations.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "30px 20px" }}>
        <p className="muted">No operations were required for this dataset.</p>
      </div>
    );
  }

  return (
    <div className="op-table-wrapper">
      <table className="op-table">
        <thead>
          <tr>
            <th>Operation</th>
            <th>Target Column</th>
            <th>Strategy</th>
            <th>Affected Rows</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {operations.map((op, idx) => (
            <tr key={`${op.operation}-${op.column ?? "all"}-${idx}`}>
              <td>
                <span className={`op-badge op-${op.operation}`}>
                  {formatOpName(op.operation)}
                </span>
              </td>
              <td style={{ fontWeight: 600 }}>{op.column ?? "All columns"}</td>
              <td>{op.strategy ?? "—"}</td>
              <td style={{ fontWeight: 600 }}>{op.affected_rows}</td>
              <td className="muted" style={{ maxWidth: 360, whiteSpace: "normal" }}>
                {op.detail ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatOpName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
