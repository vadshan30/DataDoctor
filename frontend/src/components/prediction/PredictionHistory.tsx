import { useState, useEffect } from "react";
import { getExperimentPredictions } from "../../api/prediction";
import { LoadingSpinner } from "../common/States";

interface PredictionHistoryProps {
  datasetId: number | string;
  experimentId: number | string;
}

export function PredictionHistory({ datasetId, experimentId }: PredictionHistoryProps) {
  const [predictions, setPredictions] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPredictionHistory();
  }, [datasetId, experimentId]);

  const loadPredictionHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getExperimentPredictions(datasetId, experimentId);
      setPredictions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prediction history");
    } finally {
      setLoading(false);
    }
  };

  const formatPrediction = (prediction: any) => {
    if (Array.isArray(prediction)) {
      return prediction.map(p => p.toString()).join(", ");
    }
    if (typeof prediction === "object" && prediction !== null) {
      return Object.entries(prediction)
        .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
        .join(", ");
    }
    return String(prediction);
  };

  if (loading) {
    return (
      <div className="prediction-history loading-state">
        <LoadingSpinner />
        <p>Loading prediction history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="prediction-history error-state">
        <p>❌ {error}</p>
        <button onClick={loadPredictionHistory} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  if (!predictions || !predictions.predictions || predictions.predictions.length === 0) {
    return (
      <div className="prediction-history empty-state">
        <p>No prediction history available for this experiment.</p>
      </div>
    );
  }

  return (
    <div className="prediction-history card">
      <div className="card-header">
        <h3 className="card-title">Prediction History</h3>
        <span className="prediction-count">
          {predictions.total ?? predictions.total_predictions ?? predictions.predictions.length} predictions
        </span>
      </div>

      <div className="predictions-list">
        {predictions.predictions.map((pred: any, index: number) => (
          <div key={pred.id || index} className="prediction-history-item">
            <div className="prediction-header">
              <div className="prediction-meta">
                <span className="prediction-id">#{pred.id}</span>
                <span className="prediction-timestamp">
                  {new Date(pred.created_at).toLocaleString()}
                </span>
                {pred.trained_model_id && (
                  <span className="model-id">Model ID: {pred.trained_model_id}</span>
                )}
                {pred.model_type && (
                  <span className="model-type">{pred.model_type}</span>
                )}
              </div>
            </div>

            <div className="prediction-content">
              <div className="prediction-summary">
                <div className="prediction-input">
                  <span className="label">Input:</span>
                  <div className="input-preview">
                    <pre className="input-json">
                      {JSON.stringify(pred.input_data, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="prediction-output">
                  <span className="label">Prediction:</span>
                  <div className="output-preview">
                    <code className="prediction-value">
                      {formatPrediction(pred.prediction)}
                    </code>
                  </div>
                </div>
              </div>

              <details className="prediction-details">
                <summary>Show Details</summary>
                <div className="prediction-full-data">
                  <div className="full-data-section">
                    <h5>Complete Input Data</h5>
                    <pre className="full-data-json">
                      {JSON.stringify(pred.input_data, null, 2)}
                    </pre>
                  </div>
                  <div className="full-data-section">
                    <h5>Complete Prediction</h5>
                    <pre className="full-data-json">
                      {JSON.stringify(pred.prediction, null, 2)}
                    </pre>
                  </div>
                </div>
              </details>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}