import { Cpu, FlaskConical, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorMessage } from "../common/States";
import type { ExperimentCreateRequest, MLReadyDatasetResponse } from "../../types/api";

interface ExperimentFormProps {
  preparedRuns: MLReadyDatasetResponse[];
  onTrain: (request: ExperimentCreateRequest) => void;
  loading: boolean;
  error?: string;
}

export function ExperimentForm({ preparedRuns, onTrain, loading, error }: ExperimentFormProps) {
  const [selectedMLReadyId, setSelectedMLReadyId] = useState<number>(
    preparedRuns.length > 0 ? preparedRuns[0].ml_ready_dataset_id : 0
  );
  const [experimentName, setExperimentName] = useState("Model Benchmark #1");
  const [targetColumn, setTargetColumn] = useState(
    preparedRuns.length > 0 ? preparedRuns[0].target_column : ""
  );
  const [problemType, setProblemType] = useState<"classification" | "regression">("classification");

  // Keep target_column in sync when selecting an ML-ready dataset run
  useEffect(() => {
    const found = preparedRuns.find((r) => r.ml_ready_dataset_id === Number(selectedMLReadyId));
    if (found) {
      setTargetColumn(found.target_column);
    }
  }, [selectedMLReadyId, preparedRuns]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMLReadyId || !experimentName.trim() || !targetColumn.trim() || loading) return;
    onTrain({
      ml_ready_dataset_id: Number(selectedMLReadyId),
      experiment_name: experimentName.trim(),
      target_column: targetColumn.trim(),
      problem_type: problemType,
    });
  };

  if (preparedRuns.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "40px 20px" }}>
        <FlaskConical size={32} style={{ color: "var(--teal)", marginBottom: 10 }} />
        <h3>No ML-Ready Dataset Found</h3>
        <p className="muted">
          Please run <strong>ML Preparation</strong> first to create a train/test-split dataset before training models.
        </p>
      </div>
    );
  }

  return (
    <form className="experiment-form" onSubmit={handleSubmit}>
      <div className="action-panel" style={{ flexDirection: "column", alignItems: "stretch", gap: 18 }}>
        <div className="action-info">
          <h3>Create Model Training Experiment</h3>
          <p>Trains multiple algorithms in parallel, evaluates test metrics, and selects the best model.</p>
        </div>

        <div className="prep-form-grid">
          <div className="form-group">
            <label htmlFor="exp-mlready-select">ML-Ready Dataset Version *</label>
            <select
              id="exp-mlready-select"
              className="form-select"
              value={selectedMLReadyId}
              onChange={(e) => setSelectedMLReadyId(Number(e.target.value))}
              required
            >
              {preparedRuns.map((run) => (
                <option key={run.ml_ready_dataset_id} value={run.ml_ready_dataset_id}>
                  v{run.ml_ready_dataset_id} — Target: {run.target_column} ({run.train_rows} train / {run.test_rows} test)
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="exp-name-input">Experiment Name *</label>
            <input
              id="exp-name-input"
              type="text"
              className="form-input"
              value={experimentName}
              onChange={(e) => setExperimentName(e.target.value)}
              placeholder="e.g. Churn Prediction Benchmark"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="exp-problem-type">Problem Type *</label>
            <select
              id="exp-problem-type"
              className="form-select"
              value={problemType}
              onChange={(e) => setProblemType(e.target.value as "classification" | "regression")}
              required
            >
              <option value="classification">Classification (Predict Categories)</option>
              <option value="regression">Regression (Predict Numeric Quantity)</option>
            </select>
          </div>
        </div>

        <div className="feature-category-card" style={{ padding: 14 }}>
          <div className="feature-category-header" style={{ marginBottom: 6 }}>
            <Cpu size={16} />
            <h4 style={{ fontSize: 13 }}>Automated Candidate Algorithms</h4>
          </div>
          <div className="feature-tag-list">
            {problemType === "classification" ? (
              <>
                <span className="feature-tag">RandomForestClassifier</span>
                <span className="feature-tag">LogisticRegression</span>
                <span className="feature-tag">DecisionTreeClassifier</span>
              </>
            ) : (
              <>
                <span className="feature-tag">RandomForestRegressor</span>
                <span className="feature-tag">LinearRegression</span>
                <span className="feature-tag">DecisionTreeRegressor</span>
              </>
            )}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            type="submit"
            className="button primary"
            disabled={loading || !selectedMLReadyId || !experimentName.trim()}
          >
            {loading ? (
              <>
                <RefreshCw size={16} className="spinner" />
                Training candidate models...
              </>
            ) : (
              <>
                <FlaskConical size={16} />
                Train Models
              </>
            )}
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}
    </form>
  );
}
