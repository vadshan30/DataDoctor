import { formatNumber } from "../../utils/helpers";
import type { EngineeringResultResponse } from "../../types/api";

export function FeatureEngineeringSummary({ result }: { result: EngineeringResultResponse }) {
  const colDiff = result.columns_after - result.columns_before;

  return (
    <div className="feature-summary">
      <h3 className="subheading" style={{ marginBottom: 14 }}>
        Latest Engineering Result (v{result.engineered_dataset_id})
      </h3>
      <div className="summary-stat-grid">
        <div className="stat-card">
          <span className="label">Rows</span>
          <div className="stat-comparison">
            <span className="stat-before">{formatNumber(result.rows_before, 0)}</span>
            <span className="stat-after">{formatNumber(result.rows_after, 0)}</span>
          </div>
        </div>

        <div className="stat-card">
          <span className="label">Columns</span>
          <div className="stat-comparison">
            <span className="stat-before">{result.columns_before}</span>
            <span className="stat-after">{result.columns_after}</span>
          </div>
          {colDiff !== 0 && (
            <span className="muted" style={{ fontSize: 11 }}>
              {colDiff > 0 ? `+${colDiff}` : `${colDiff}`} total columns
            </span>
          )}
        </div>

        <div className="stat-card">
          <span className="label">Features Added</span>
          <span className="value" style={{ color: "var(--teal)" }}>
            +{result.features_added}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Features Pruned</span>
          <span className="value" style={{ color: result.features_removed > 0 ? "var(--warning)" : "var(--ink)" }}>
            -{result.features_removed}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Status</span>
          <span className="status-pill" style={{ justifySelf: "start", marginTop: 4 }}>
            {result.engineering_status}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Engineered At</span>
          <span style={{ fontSize: 12, marginTop: 4, fontWeight: 600, color: "var(--ink)" }}>
            {new Date(result.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {result.new_feature_names && result.new_feature_names.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 14, margin: "0 0 8px", color: "var(--ink)" }}>
            Generated Features ({result.new_feature_names.length})
          </h4>
          <div className="feature-pill-list">
            {result.new_feature_names.map((name) => (
              <span key={name} className="feature-pill">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
