interface PreprocessingOp {
  operation?: string;
  strategy?: string;
  detail?: string;
  [key: string]: unknown;
}

export function PreparationOperations({ operations }: { operations: Record<string, unknown>[] }) {
  if (!operations || operations.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "30px 20px" }}>
        <p className="muted">No preprocessing operations performed.</p>
      </div>
    );
  }

  return (
    <div className="op-table-wrapper">
      <table className="op-table">
        <thead>
          <tr>
            <th>Operation</th>
            <th>Strategy</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {operations.map((op, idx) => {
            const castOp = op as PreprocessingOp;
            const opName = String(castOp.operation || castOp.name || "Preprocessing");
            return (
              <tr key={`${opName}-${idx}`}>
                <td>
                  <span className="op-badge">{formatOpName(opName)}</span>
                </td>
                <td>{String(castOp.strategy || "Standard")}</td>
                <td className="muted" style={{ maxWidth: 400, whiteSpace: "normal" }}>
                  {String(castOp.detail || JSON.stringify(op))}
                </td>
              </tr>
            );
          })}
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
