import { Award, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { formatNumber } from "../../utils/helpers";
import type { ModelResultResponse } from "../../types/api";

interface ModelComparisonProps {
  models: ModelResultResponse[];
  bestModelId: number | null;
  problemType: string;
}

export function ModelComparison({ models, bestModelId, problemType }: ModelComparisonProps) {
  if (!models || models.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "30px 20px" }}>
        <p className="muted">No trained model results available.</p>
      </div>
    );
  }

  return (
    <div className="model-comparison-container">
      <h3 className="subheading" style={{ marginBottom: 14 }}>
        Trained Models Benchmark ({models.length})
      </h3>
      <div className="model-card-grid">
        {models.map((model) => (
          <ModelResultCard
            key={model.model_id}
            model={model}
            isBest={bestModelId === model.model_id}
            problemType={problemType}
          />
        ))}
      </div>
    </div>
  );
}

function ModelResultCard({
  model,
  isBest,
  problemType,
}: {
  model: ModelResultResponse;
  isBest: boolean;
  problemType: string;
}) {
  const [showParams, setShowParams] = useState(false);

  return (
    <div className={`model-card ${isBest ? "is-best" : ""}`}>
      {isBest && (
        <span className="best-badge">
          <Award size={12} style={{ marginRight: 4 }} /> Best Model
        </span>
      )}

      <div className="model-card-header">
        <div>
          <h4>{model.model_name}</h4>
          <span className="muted" style={{ fontSize: 12 }}>
            Algorithm: {model.algorithm}
          </span>
        </div>
        <span className="status-pill">{model.status}</span>
      </div>

      {model.metrics && (
        <div className="metrics-grid">
          {problemType === "classification" ? (
            <>
              <div className="metric-item">
                <span className="m-label">F1 Score</span>
                <span className="m-val">{formatNumber(model.metrics.f1)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">Accuracy</span>
                <span className="m-val">{formatNumber(model.metrics.accuracy)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">Precision</span>
                <span className="m-val">{formatNumber(model.metrics.precision)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">Recall</span>
                <span className="m-val">{formatNumber(model.metrics.recall)}</span>
              </div>
            </>
          ) : (
            <>
              <div className="metric-item">
                <span className="m-label">R² Score</span>
                <span className="m-val">{formatNumber(model.metrics.r2)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">RMSE</span>
                <span className="m-val">{formatNumber(model.metrics.rmse)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">MAE</span>
                <span className="m-val">{formatNumber(model.metrics.mae)}</span>
              </div>
              <div className="metric-item">
                <span className="m-label">MSE</span>
                <span className="m-val">{formatNumber(model.metrics.mse)}</span>
              </div>
            </>
          )}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)" }}>
        <span>
          Rows: <strong>{model.training_rows}</strong> train / <strong>{model.validation_rows}</strong> val
        </span>
        <span>Features: <strong>{model.feature_count}</strong></span>
      </div>

      {model.hyperparameters && (
        <div>
          <button
            type="button"
            className="text-button"
            onClick={() => setShowParams((v) => !v)}
            style={{ fontSize: 12, padding: 0 }}
          >
            {showParams ? (
              <>
                Hide Hyperparameters <ChevronUp size={12} />
              </>
            ) : (
              <>
                Show Hyperparameters <ChevronDown size={12} />
              </>
            )}
          </button>

          {showParams && (
            <pre className="hyperparams-preview" style={{ marginTop: 8 }}>
              {JSON.stringify(model.hyperparameters, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
