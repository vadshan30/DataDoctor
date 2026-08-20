import type { FeatureEngineeringOperation } from "../../types/api";

export function FeatureEngineeringOperationList({ operations }: { operations: FeatureEngineeringOperation[] }) {
  if (!operations || operations.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "30px 20px" }}>
        <p className="muted">No feature engineering operations were performed.</p>
      </div>
    );
  }

  return (
    <div className="op-table-wrapper">
      <table className="op-table">
        <thead>
          <tr>
            <th>Operation</th>
            <th>Source Column(s)</th>
            <th>Strategy</th>
            <th>Features Created / Action</th>
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
              <td style={{ fontWeight: 600 }}>{op.column ?? "Dataset columns"}</td>
              <td>{op.strategy ?? "—"}</td>
              <td style={{ fontSize: 12 }}>
                {op.new_features && op.new_features.length > 0 ? (
                  <span style={{ fontFamily: "monospace", color: "var(--teal)" }}>
                    {op.new_features.join(", ")}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td className="muted" style={{ maxWidth: 320, whiteSpace: "normal" }}>
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
