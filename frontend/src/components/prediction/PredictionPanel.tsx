import { useState, useEffect } from "react";
import { predictSingle } from "../../api/prediction";
import { getLatestPreparedDataset } from "../../api/mlPreparation";
import { PredictionRequest } from "../../types/api";
import { Button } from "../common/Button";
import { LoadingSpinner } from "../common/States";

interface PredictionPanelProps {
  datasetId: number | string;
  experimentId: number | string;
  modelId: number | string;
  onPredictionComplete?: (result: any) => void;
}

export function PredictionPanel({
  datasetId,
  experimentId,
  modelId,
  onPredictionComplete,
}: PredictionPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preparedDataset, setPreparedDataset] = useState<any>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [predictionResult, setPredictionResult] = useState<any>(null);

  useEffect(() => {
    loadPreparedDataset();
  }, [datasetId]);

  const loadPreparedDataset = async () => {
    try {
      const dataset = await getLatestPreparedDataset(datasetId);
      setPreparedDataset(dataset);
      // Initialize form with feature names (excluding target)
      const initialForm: Record<string, any> = {};
      if (dataset.feature_names) {
        dataset.feature_names.forEach((feature: string) => {
          if (feature !== dataset.target_column) {
            initialForm[feature] = "";
          }
        });
      }
      setFormData(initialForm);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prepared dataset");
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handlePredict = async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setPredictionResult(null);

    try {
      const request: PredictionRequest = {
        features: formData
      };

      const result = await predictSingle(datasetId, experimentId, modelId, request);
      setPredictionResult(result);
      onPredictionComplete?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const getInputType = (fieldName: string): string => {
    // Infer input type from field name or dataset metadata
    if (preparedDataset?.numeric_columns?.includes(fieldName)) {
      return "number";
    } else if (preparedDataset?.categorical_columns?.includes(fieldName)) {
      return "text"; // Could be select for known categories
    } else if (fieldName.toLowerCase().includes("is_") || fieldName.toLowerCase().includes("has_")) {
      return "checkbox";
    }
    return "text";
  };

  const renderInputField = (fieldName: string) => {
    const inputType = getInputType(fieldName);
    const value = formData[fieldName] || "";

    switch (inputType) {
      case "number":
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.valueAsNumber || "")}
            placeholder="Enter value"
            className="input-field"
          />
        );
      case "checkbox":
        return (
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => handleInputChange(fieldName, e.target.checked)}
            className="checkbox-input"
          />
        );
      case "text":
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            placeholder="Enter value"
            className="input-field"
          />
        );
      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleInputChange(fieldName, e.target.value)}
            placeholder="Enter value"
            className="input-field"
          />
        );
    }
  };

  if (!preparedDataset) {
    return (
      <div className="prediction-panel loading-state">
        <LoadingSpinner />
        <p>Loading prepared dataset...</p>
      </div>
    );
  }

  return (
    <div className="prediction-panel card">
      <div className="card-header">
        <h3 className="card-title">Single Prediction</h3>
        <div className="model-info">
          <span>Model: {preparedDataset.model_name || "Selected Model"}</span>
          <span>Experiment: {experimentId}</span>
        </div>
      </div>

      <div className="prediction-form">
        {error && (
          <div className="error-banner">
            <p>❌ {error}</p>
          </div>
        )}

        <div className="form-grid">
          {Object.keys(formData).map(fieldName => (
            <div key={fieldName} className="form-field">
              <label className="field-label">
                {fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </label>
              {renderInputField(fieldName)}
            </div>
          ))}
        </div>

        <div className="prediction-actions">
          <Button
            onClick={handlePredict}
            disabled={loading}
            loading={loading}
            className="predict-button"
          >
            {loading ? "Predicting..." : "Make Prediction"}
          </Button>
        </div>

        {predictionResult && (
          <div className="prediction-result">
            <h4>Prediction Result</h4>
            <div className="result-content">
              <div className="result-prediction">
                <span className="label">Prediction:</span>
                <span className="value prediction-value">
                  {JSON.stringify(predictionResult.prediction)}
                </span>
              </div>
              {predictionResult.confidence && (
                <div className="result-confidence">
                  <span className="label">Confidence:</span>
                  <span className="value">{predictionResult.confidence}</span>
                </div>
              )}
              <div className="result-metadata">
                <span className="label">Model:</span>
                <span className="value">{predictionResult.model_name}</span>
              </div>
              <div className="result-metadata">
                <span className="label">Timestamp:</span>
                <span className="value">
                  {new Date(predictionResult.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}