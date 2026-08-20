import { Trophy, TrendingUp, Award } from "lucide-react";
import { ModelComparisonResponse } from "../../types/api";

interface ModelRankingProps {
  comparison: ModelComparisonResponse;
  onModelSelect?: (modelId: number) => void;
}

export function ModelRanking({ comparison, onModelSelect }: ModelRankingProps) {
  const formatScore = (score: number | null) => {
    if (score === null) return "N/A";
    return score.toFixed(4);
  };

  const getMetricColor = (rank: number) => {
    if (rank === 1) return "metric-best";
    if (rank === 2) return "metric-good";
    if (rank === 3) return "metric-fair";
    return "";
  };

  return (
    <div className="model-ranking card">
      <div className="card-header">
        <Trophy size={20} />
        <h3 className="card-title">Model Ranking</h3>
        <span className="ranking-summary">
          Ranked by {comparison.primary_metric} (lower is better for {comparison.secondary_metric})
        </span>
      </div>

      <div className="ranking-list">
        {comparison.ranked_models.map((model) => (
          <div
            key={model.trained_model_id}
            className={`ranking-item ${model.is_best ? "best-model" : ""}`}
            onClick={() => onModelSelect?.(model.model_id)}
            style={{ cursor: onModelSelect ? "pointer" : "default" }}
          >
            <div className="rank-section">
              <div className={`rank-badge ${getMetricColor(model.rank)}`}>{model.rank}</div>
              {model.is_best && (
                <div className="best-award">
                  <Award size={16} />
                </div>
              )}
            </div>

            <div className="model-info">
              <h4 className="model-name">{model.model_name}</h4>
              <div className="model-details">
                <span className="algorithm">{model.algorithm}</span>
                <span className="model-type">{model.model_type}</span>
                <span className="status">{model.status}</span>
              </div>
            </div>

            <div className="metrics-section">
              <div className="metric-row">
                <span className="metric-label">Primary:</span>
                <span className="metric-value primary">
                  {formatScore(model.primary_metric_value)}
                </span>
              </div>
              {model.metrics && Object.keys(model.metrics).length > 0 && (
                <div className="additional-metrics">
                  {Object.entries(model.metrics)
                    .filter(([key]) => key !== comparison.primary_metric)
                    .slice(0, 2)
                    .map(([key, value]) => (
                      <div key={key} className="metric-row">
                        <span className="metric-label">{key}:</span>
                        <span className="metric-value secondary">
                          {(value as number).toFixed(4)}
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>

            <div className="rank-score">
              <TrendingUp size={16} />
              <span className="rank-score-value">
                {(comparison.primary_metric === "rmse" || comparison.secondary_metric === "rmse")
                  ? formatScore(model.primary_metric_value)
                  : formatScore(model.primary_metric_value)
                }
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="ranking-footer">
        <div className="ranking-info">
          <span>🏆 Best Model: {comparison.ranked_models[0]?.model_name || "N/A"}</span>
          <span>Primary Metric: {comparison.primary_metric}</span>
          {comparison.secondary_metric && (
            <span>Secondary Metric: {comparison.secondary_metric}</span>
          )}
        </div>
      </div>
    </div>
  );
}