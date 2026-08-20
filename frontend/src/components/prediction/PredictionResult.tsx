import { CheckCircle2, AlertCircle, Clock, TrendingUp, BarChart3, Activity } from "lucide-react";

interface PredictionResultProps {
  result: any;
  modelName: string;
  experimentName: string;
  timestamp: string;
}

export function PredictionResult({ result, modelName, experimentName, timestamp }: PredictionResultProps) {
  const renderPrediction = () => {
    const prediction = result.prediction;
    const problemType = result.problem_type || "unknown";

    if (Array.isArray(prediction)) {
      return (
        <div className="prediction-array">
          {prediction.map((pred, idx) => (
            <div key={idx} className="prediction-item">
              <span className="label">Sample {idx + 1}:</span>
              <span className="value">{JSON.stringify(pred)}</span>
            </div>
          ))}
        </div>
      );
    }

    if (typeof prediction === "object" && prediction !== null) {
      return (
        <div className="prediction-object">
          {Object.entries(prediction).map(([key, value]) => (
            <div key={key} className="prediction-item">
              <span className="label">{key}:</span>
              <span className="value">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="prediction-single">
        <span className="value prediction-value">{prediction.toString()}</span>
      </div>
    );
  };

  const getResultStatus = () => {
    if (!result) return "pending";
    return "completed";
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
    <div className="prediction-result card">
      <div className="card-header">
        <div className="result-header">
          <div className="result-info">
            <h3 className="card-title">Prediction Result</h3>
            <div className="result-meta">
              <span className="status-indicator">
                {getStatusIcon(getResultStatus())}
                {getResultStatus()}
              </span>
              <span>Model: {modelName}</span>
              <span>Experiment: {experimentName}</span>
              <span>Time: {new Date(timestamp).toLocaleString()}</span>
            </div>
          </div>
          {result.confidence && (
            <div className="confidence-badge">
              <TrendingUp size={16} />
              <span>{result.confidence}</span>
            </div>
          )}
        </div>
      </div>

      <div className="result-content">
        <div className="prediction-section">
          <h4 className="section-title">
            {result.problem_type === "classification" ? "Classification" : "Regression"} Prediction
          </h4>
          <div className="prediction-display">
            {renderPrediction()}
          </div>
        </div>

        {result.input_data && (
          <div className="input-data-section">
            <h4 className="section-title">Input Features</h4>
            <div className="input-data-display">
              <pre className="input-data-json">
                {JSON.stringify(result.input_data, null, 2)}
              </pre>
            </div>
          </div>
        )}

        <div className="result-metadata">
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="label">Model Type:</span>
              <span className="value">{result.model_type}</span>
            </div>
            <div className="metadata-item">
              <span className="label">Algorithm:</span>
              <span className="value">{result.algorithm}</span>
            </div>
            <div className="metadata-item">
              <span className="label">Problem Type:</span>
              <span className="value">{result.problem_type}</span>
            </div>
            <div className="metadata-item">
              <span className="label">Model ID:</span>
              <span className="value">{result.model_id}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}