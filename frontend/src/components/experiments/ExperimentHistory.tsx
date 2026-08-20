import { ChevronDown, ChevronUp, History } from "lucide-react";
import { useState } from "react";
import { ModelComparison } from "./ModelComparison";
import type { ExperimentResponse } from "../../types/api";

export function ExperimentHistory({ experiments }: { experiments: ExperimentResponse[] }) {
  if (!experiments || experiments.length === 0) {
    return null;
  }

  return (
    <div className="history-section">
      <h3 className="subheading" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <History size={18} /> Experiment History ({experiments.length})
      </h3>
      <div className="history-list">
        {experiments.map((exp) => (
          <HistoryExperimentCard key={exp.experiment_id} experiment={exp} />
        ))}
      </div>
    </div>
  );
}

function HistoryExperimentCard({ experiment }: { experiment: ExperimentResponse }) {
  const [expanded, setExpanded] = useState(false);

  const bestModelName =
    experiment.best_model_id != null && experiment.models[experiment.best_model_id]
      ? experiment.models[experiment.best_model_id].model_name
      : "None";

  return (
    <div className="history-card">
      <div className="history-header">
        <div className="history-meta">
          <strong>Experiment #{experiment.experiment_id} — {experiment.name}</strong>
          <span className="type-badge">{experiment.problem_type.toUpperCase()}</span>
          <span className="status-pill">{experiment.status}</span>
          <span className="muted">{new Date(experiment.created_at).toLocaleString()}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 13 }}>
            Best Model: <strong style={{ color: "var(--teal)" }}>{bestModelName}</strong> ({experiment.best_metric ?? "score"}: <strong>{experiment.best_score != null ? experiment.best_score.toFixed(4) : "—"}</strong>)
          </span>
          <button
            type="button"
            className="text-button"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? (
              <>
                Hide models <ChevronUp size={14} />
              </>
            ) : (
              <>
                View models ({experiment.models.length}) <ChevronDown size={14} />
              </>
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 12 }}>
          <ModelComparison
            models={experiment.models}
            bestModelId={experiment.best_model_id}
            problemType={experiment.problem_type}
          />
        </div>
      )}
    </div>
  );
}
