import { CheckCircle2 } from "lucide-react";
import { formatNumber } from "../../utils/helpers";
import type { MLReadyDatasetResponse } from "../../types/api";

export function PreparationSummary({ result }: { result: MLReadyDatasetResponse }) {
  return (
    <div className="prep-summary">
      <h3 className="subheading" style={{ marginBottom: 14 }}>
        Latest ML-Ready Dataset (v{result.ml_ready_dataset_id})
      </h3>
      <div className="summary-stat-grid">
        <div className="stat-card">
          <span className="label">Target Column</span>
          <strong style={{ fontSize: 18, color: "var(--teal)" }}>{result.target_column}</strong>
        </div>

        <div className="stat-card">
          <span className="label">Source Artifact</span>
          <span className="type-badge" style={{ justifySelf: "start", marginTop: 4 }}>
            {result.source_dataset_type.toUpperCase()}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Train / Test Split</span>
          <div className="stat-comparison">
            <span className="stat-after" style={{ color: "var(--ink)" }}>{formatNumber(result.train_rows, 0)} train</span>
            <span className="muted">/ {formatNumber(result.test_rows, 0)} test</span>
          </div>
        </div>

        <div className="stat-card">
          <span className="label">Processed Features</span>
          <div className="stat-comparison">
            <span className="stat-before">{result.original_feature_count} orig</span>
            <span className="stat-after">{result.processed_feature_count} processed</span>
          </div>
        </div>

        <div className="stat-card">
          <span className="label">Preprocessor Status</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--success)", fontWeight: 600, fontSize: 13, marginTop: 4 }}>
            <CheckCircle2 size={16} /> Preprocessor Saved
          </div>
        </div>

        <div className="stat-card">
          <span className="label">Prepared At</span>
          <span style={{ fontSize: 12, marginTop: 4, fontWeight: 600, color: "var(--ink)" }}>
            {new Date(result.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {result.feature_names && result.feature_names.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 14, margin: "0 0 8px", color: "var(--ink)" }}>
            Processed Feature Names ({result.feature_names.length})
          </h4>
          <div className="feature-pill-list">
            {result.feature_names.map((name) => (
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
