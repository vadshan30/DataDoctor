import { useState, useEffect } from "react";
import { predictBatch } from "../../api/prediction";
import { getLatestPreparedDataset } from "../../api/mlPreparation";
import { BatchPredictionRequest } from "../../types/api";
import { Button } from "../common/Button";
import { LoadingSpinner } from "../common/States";

interface BatchPredictionPanelProps {
  datasetId: number | string;
  experimentId: number | string;
  modelId: number | string;
  onBatchComplete?: (result: any) => void;
}

export function BatchPredictionPanel({
  datasetId,
  experimentId,
  modelId,
  onBatchComplete,
}: BatchPredictionPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preparedDataset, setPreparedDataset] = useState<any>(null);
  const [structuredData, setStructuredData] = useState<Record<string, any>[]>([]);
  const [predictionResult, setPredictionResult] = useState<any>(null);

  useEffect(() => {
    loadPreparedDataset();
  }, [datasetId]);

  const loadPreparedDataset = async () => {
    try {
      const dataset = await getLatestPreparedDataset(datasetId);
      setPreparedDataset(dataset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prepared dataset");
    }
  };

  const handleStructuredDataChange = (index: number, field: string, value: any) => {
    const newData = [...structuredData];
    newData[index] = { ...newData[index], [field]: value };
    setStructuredData(newData);
  }

  const addRow = () => {
    if (!preparedDataset?.feature_names) return;
    const newRow: Record<string, any> = {};
    preparedDataset.feature_names.forEach((feature: string) => {
      if (feature !== preparedDataset.target_column) {
        newRow[feature] = "";
      }
    });
    setStructuredData(prev => [...prev, newRow]);
  }

  const removeRow = (index: number) => {
    setStructuredData(prev => prev.filter((_, i) => i !== index));
  }

  const handlePredictBatch = async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setPredictionResult(null);

    try {
      if (structuredData.length === 0) {
        throw new Error("Add at least one input row before running batch prediction.");
      }
      const request: BatchPredictionRequest = { rows: structuredData };

      const result = await predictBatch(datasetId, experimentId, modelId, request);
      setPredictionResult(result);
      onBatchComplete?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const renderStructuredInput = () => {
    if (!preparedDataset?.feature_names) return null;

    return (
      <div className="structured-input">
        <div className="input-header">
          <h4>Structured Input</h4>
          <Button onClick={addRow} className="add-row-button">
            Add Row
          </Button>
        </div>

        {structuredData.map((row, index) => (
          <div key={index} className="data-row">
            <div className="row-header">
              <span>Row {index + 1}</span>
              <Button
                onClick={() => removeRow(index)}
                className="remove-row-button"
              >
                Remove
              </Button>
            </div>
            <div className="row-fields">
              {preparedDataset.feature_names
                .filter((field: string) => field !== preparedDataset.target_column)
                .map((fieldName: string) => (
                  <div key={fieldName} className="row-field">
                    <label>{fieldName}</label>
                    <input
                      type="text"
                      value={row[fieldName] || ""}
                      onChange={(e) => handleStructuredDataChange(index, fieldName, e.target.value)}
                      placeholder={fieldName}
                    />
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="batch-prediction-panel card">
      <div className="card-header">
        <h3 className="card-title">Batch Prediction</h3>
        <div className="model-info">
          <span>Model: {preparedDataset?.model_name || "Selected Model"}</span>
          <span>Experiment: {experimentId}</span>
        </div>
      </div>

      <div className="prediction-content">
        {error && (
          <div className="error-banner">
            <p>❌ {error}</p>
          </div>
        )}

        {renderStructuredInput()}

        <div className="prediction-actions">
          <Button
            onClick={handlePredictBatch}
            disabled={loading}
            loading={loading}
            className="predict-batch-button"
          >
            {loading ? "Predicting..." : "Run Batch Prediction"}
          </Button>
        </div>

        {predictionResult && (
          <div className="batch-result">
            <h4>Batch Prediction Results</h4>
            <div className="result-summary">
              <div className="result-stat">
                <span>Model:</span>
                <strong>{predictionResult.model_name}</strong>
              </div>
              <div className="result-stat">
                <span>Predictions:</span>
                <strong>{predictionResult.predictions?.length || 0}</strong>
              </div>
              <div className="result-stat">
                <span>Input Rows:</span>
                <strong>{predictionResult.input_data?.length || 0}</strong>
              </div>
            </div>

            {predictionResult.predictions && (
              <div className="predictions-table">
                <h5>Predictions</h5>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Prediction</th>
                        {predictionResult.input_data?.[0] &&
                          Object.keys(predictionResult.input_data[0]).map(key => (
                            <th key={key}>{key}</th>
                          ))}
                      </tr>
                    </thead>
                    <tbody>
                      {predictionResult.predictions.map((pred: any, index: number) => (
                        <tr key={index}>
                          <td>{index + 1}</td>
                          <td>{JSON.stringify(pred)}</td>
                          {predictionResult.input_data?.[index] &&
                            Object.entries(predictionResult.input_data[index]).map(([key, value]) => (
                              <td key={key}>{String(value)}</td>
                            ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}