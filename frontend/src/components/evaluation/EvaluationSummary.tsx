import { CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { EvaluationSummaryResponse } from "../../types/api";

interface EvaluationSummaryProps {
  summary: EvaluationSummaryResponse;
}

export function EvaluationSummary({ summary }: EvaluationSummaryProps) {
  const formatScore = (score: number | null) => {
    if (score === null) return "N/A";
    return score.toFixed(4);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 size={16} className="status-completed" />;
      case "failed":
        return <AlertCircle size={16} className="status-failed" />;
      default:
        return <Clock size={16} className="status-pending" />;
    }
  };

  return (
    <div className="evaluation-summary card">
      <div className="card-header">
        <h3 className="card-title">Evaluation Summary</h3>
        <span className="status-badge">
          {getStatusIcon(summary.status)}
          {summary.status}
        </span>
      </div>

      <div className="metrics-grid">
        <div className="metric-item">
          <span className="metric-label">Experiment</span>
          <strong className="metric-value">{summary.experiment_name}</strong>
        </div>

        <div className="metric-item">
          <span className="metric-label">Problem Type</span>
          <strong className="metric-value">{summary.problem_type}</strong>
        </div>

        <div className="metric-item">
          <span className="metric-label">Models Evaluated</span>
          <strong className="metric-value">{summary.evaluations.length}</strong>
        </div>

        {summary.primary_metric && (
          <div className="metric-item">
            <span className="metric-label">Primary Metric</span>
            <strong className="metric-value">{summary.primary_metric}</strong>
          </div>
        )}

        {summary.best_score !== null && (
          <div className="metric-item">
            <span className="metric-label">Best Score</span>
            <strong className="metric-value best-score">
              {formatScore(summary.best_score)}
            </strong>
          </div>
        )}

        {summary.best_model_name && (
          <div className="metric-item">
            <span className="metric-label">Best Model</span>
            <strong className="metric-value">{summary.best_model_name}</strong>
          </div>
        )}

        <div className="metric-item">
          <span className="metric-label">Evaluated At</span>
          <strong className="metric-value">
            {new Date(summary.evaluations[0]?.created_at).toLocaleString()}
          </strong>
        </div>
      </div>
    </div>
  );
}