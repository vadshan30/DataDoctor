import { Award } from "lucide-react";
import { formatNumber } from "../../utils/helpers";
import type { ExperimentResponse } from "../../types/api";

export function ExperimentSummary({ experiment }: { experiment: ExperimentResponse }) {
  const bestModelName =
    experiment.best_model_id != null && experiment.models[experiment.best_model_id]
      ? experiment.models[experiment.best_model_id].model_name
      : "None";

  return (
    <div className="experiment-summary">
      <h3 className="subheading" style={{ marginBottom: 14 }}>
        Experiment Results — {experiment.name}
      </h3>
      <div className="summary-stat-grid">
        <div className="stat-card" style={{ borderLeft: "4px solid var(--teal)" }}>
          <span className="label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Award size={14} style={{ color: "var(--teal)" }} /> Best Model
          </span>
          <strong style={{ fontSize: 18, color: "var(--teal)" }}>{bestModelName}</strong>
        </div>

        <div className="stat-card">
          <span className="label">Primary Metric ({experiment.best_metric?.toUpperCase() ?? "—"})</span>
          <span className="value" style={{ color: "var(--teal)" }}>
            {formatNumber(experiment.best_score)}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Problem Type</span>
          <span className="type-badge" style={{ justifySelf: "start", marginTop: 4 }}>
            {experiment.problem_type.toUpperCase()}
          </span>
        </div>

        <div className="stat-card">
          <span className="label">Models Evaluated</span>
          <span className="value">{experiment.models.length}</span>
        </div>

        <div className="stat-card">
          <span className="label">Experiment Status</span>
          <span className="status-pill" style={{ justifySelf: "start", marginTop: 4 }}>
            {experiment.status}
          </span>
        </div>

        {experiment.total_training_duration != null && (
          <div className="stat-card">
            <span className="label">Training Duration</span>
            <span style={{ fontSize: 13, marginTop: 4, fontWeight: 600, color: "var(--ink)" }}>
              {experiment.total_training_duration.toFixed(2)}s
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
