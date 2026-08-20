import { CheckCircle2, AlertCircle, Clock, TrendingUp } from "lucide-react";
import { ModelEvaluationResponse } from "../../types/api";
import { ConfusionMatrix } from "./ConfusionMatrix";

interface ModelEvaluationCardProps {
  evaluation: ModelEvaluationResponse;
}

export function ModelEvaluationCard({ evaluation }: ModelEvaluationCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 size={16} className="status-completed" />;
      case "failed":
        return <AlertCircle size={16} className="status-failed" />;
      case "skipped":
        return <Clock size={16} className="status-skipped" />;
      default:
        return <Clock size={16} className="status-pending" />;
    }
  };

  const getProblemTypeMetrics = (modelType: string) => {
    if (modelType === "classifier") {
      return ["accuracy", "precision", "recall", "f1"];
    } else if (modelType === "regressor") {
      return ["r2", "rmse", "mae"];
    }
    return [];
  };

  const problemTypeMetrics = getProblemTypeMetrics(evaluation.model_type);
  const visibleMetrics = evaluation.metrics
    ? Object.keys(evaluation.metrics).filter(key =>
        problemTypeMetrics.includes(key)
      )
    : [];

  return (
    <div className="model-evaluation-card card">
      <div className="card-header">
        <div className="model-info">
          <h4 className="card-title">{evaluation.model_name}</h4>
          <div className="model-meta">
            <span className="algorithm">{evaluation.algorithm}</span>
            <span className="model-type">{evaluation.model_type}</span>
          </div>
        </div>

        <div className="status-section">
          {getStatusIcon(evaluation.evaluation_status)}
          <span className={`status-text ${evaluation.evaluation_status}`}>{evaluation.evaluation_status}</span>
          {evaluation.is_best && <span className="badge best">🏆 Best</span>}
        </div>
      </div>

      {evaluation.evaluation_status === "completed" && evaluation.metrics && (
        <div className="metrics-section">
          <h5 className="section-title">Metrics</h5>
          {visibleMetrics.length > 0 ? (
            <div className="metrics-grid">
              {visibleMetrics.map(key => (
                <div key={key} className="metric-item">
                  <span className="metric-label">{key}</span>
                  <strong className="metric-value">
                    {(evaluation.metrics as Record<string, number>)[key]?.toFixed(4) || "N/A"}
                  </strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-metrics">
              <p>No detailed metrics available for {evaluation.model_type}</p>
            </div>
          )}
          {evaluation.model_type === "classifier" &&
            Array.isArray(evaluation.metrics.confusion_matrix) && (
              <ConfusionMatrix
                matrix={evaluation.metrics.confusion_matrix as number[][]}
                labels={Array.isArray(evaluation.metrics.confusion_matrix_labels)
                  ? evaluation.metrics.confusion_matrix_labels.map(String)
                  : undefined}
              />
            )}
        </div>
      )}

      {evaluation.error_message && (
        <div className="error-section">
          <AlertCircle size={14} />
          <span className="error-text">{evaluation.error_message}</span>
        </div>
      )}

      <div className="card-footer">
        <div className="meta-info">
          <span>Model ID: {evaluation.trained_model_id}</span>
          {evaluation.created_at && (
            <span>Created: {new Date(evaluation.created_at).toLocaleString()}</span>
          )}
        </div>

        {evaluation.primary_metric_value !== null && (
          <div className="primary-metric">
            <TrendingUp size={14} />
            <span>{evaluation.primary_metric}: {evaluation.primary_metric_value.toFixed(4)}</span>
          </div>
        )}
      </div>
    </div>
  );
}