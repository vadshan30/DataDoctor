import { History } from "lucide-react";
import { formatNumber } from "../../utils/helpers";
import type { MLReadyDatasetResponse } from "../../types/api";

export function PreparationHistory({ runs }: { runs: MLReadyDatasetResponse[] }) {
  if (!runs || runs.length === 0) {
    return null;
  }

  return (
    <div className="history-section">
      <h3 className="subheading" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <History size={18} /> ML Preparation Run History ({runs.length})
      </h3>
      <div className="history-list">
        {runs.map((run) => (
          <div key={run.ml_ready_dataset_id} className="history-card">
            <div className="history-header">
              <div className="history-meta">
                <strong>ML-Ready #{run.ml_ready_dataset_id}</strong>
                <span className="status-pill">{run.status}</span>
                <span className="muted">{new Date(run.created_at).toLocaleString()}</span>
              </div>
              <div style={{ fontSize: 13 }}>
                Target: <strong style={{ color: "var(--teal)" }}>{run.target_column}</strong> | Train/Test: <strong>{formatNumber(run.train_rows, 0)} / {formatNumber(run.test_rows, 0)}</strong> ({Math.round(run.test_size * 100)}% test) | Features: <strong>{run.processed_feature_count}</strong>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
