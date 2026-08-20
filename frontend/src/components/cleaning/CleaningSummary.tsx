import { formatNumber } from "../../utils/helpers";
import type { CleaningResultResponse } from "../../types/api";

export function CleaningSummary({ result }: { result: CleaningResultResponse }) {
  const rowDiff = result.rows_after - result.rows_before;
  const colDiff = result.columns_after - result.columns_before;

  return (
    <div className="cleaning-summary">
      <h3 className="subheading" style={{ marginBottom: 14 }}>
        Latest Cleaning Result (v{result.cleaned_dataset_id})
      </h3>
      <div className="summary-stat-grid">
        <div className="stat-card">
          <span className="label">Rows</span>
          <div className="stat-comparison">
            <span className="stat-before">{formatNumber(result.rows_before, 0)}</span>
            <span className="stat-after">{formatNumber(result.rows_after, 0)}</span>
          </div>
          {rowDiff !== 0 && (
            <span className="muted" style={{ fontSize: 11 }}>
              {rowDiff > 0 ? `+${rowDiff}` : `${rowDiff}`} rows
            </span>
          )}
        </div>

        <div className="stat-card">
          <span className="label">Columns</span>
          <div className="stat-comparison">
            <span className="stat-before">{result.columns_before}</span>
            <span className="stat-after">{result.columns_after}</span>
          </div>
          {colDiff !== 0 && (
            <span className="muted" style={{ fontSize: 11 }}>
              {colDiff > 0 ? `+${colDiff}` : `${colDiff}`} cols
            </span>
          )}
        </div>

        <div className="stat-card">
          <span className="label">Missing Values Imputed</span>
          <span className="value" style={{ color: "var(--teal)" }}>
            {formatNumber(result.missing_values_handled, 0)}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Duplicate Rows Removed</span>
          <span className="value" style={{ color: result.duplicates_removed > 0 ? "var(--warning)" : "var(--ink)" }}>
            {formatNumber(result.duplicates_removed, 0)}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Cleaning Status</span>
          <span className="status-pill" style={{ justifySelf: "start", marginTop: 4 }}>
            {result.cleaning_status}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Cleaned At</span>
          <span style={{ fontSize: 12, marginTop: 4, fontWeight: 600, color: "var(--ink)" }}>
            {new Date(result.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
